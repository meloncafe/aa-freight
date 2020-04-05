from datetime import timedelta
from unittest.mock import patch, Mock
import math

from dhooks_lite import Embed

from django.contrib.auth.models import User 
from django.core.exceptions import ValidationError
from django.utils.timezone import now

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.eveonline.providers import ObjectNotFound

from esi.models import Token
from esi.errors import TokenExpiredError, TokenInvalidError

from . import TempDisconnectPricingSaveHandler
from ..app_settings import (
    FREIGHT_OPERATION_MODE_MY_ALLIANCE,
    FREIGHT_OPERATION_MODE_MY_CORPORATION,
    FREIGHT_OPERATION_MODE_CORP_IN_ALLIANCE,
    FREIGHT_OPERATION_MODE_CORP_PUBLIC,
    FREIGHT_OPERATION_MODES
)
from ..models import Contract, ContractHandler, EveEntity, Location, Pricing
from .testdata import (
    characters_data, 
    create_locations, 
    create_entities_from_characters,
    contracts_data,    
)
from ..utils import set_test_logger, NoSocketsTestCase


MODULE_PATH = 'freight.models'
logger = set_test_logger(MODULE_PATH, __file__)


class TestPricing(NoSocketsTestCase):

    def setUp(self):                
        create_entities_from_characters()
        
        # 1 user
        character = EveCharacter.objects.get(character_id=90000001)        
        alliance = EveEntity.objects.get(id=character.alliance_id)
        
        self.handler = ContractHandler.objects.create(
            organization=alliance,
            operation_mode=FREIGHT_OPERATION_MODE_MY_ALLIANCE
        )

        self.location_1, self.location_2, self.location_3 = create_locations()

    def test_create_pricings(self):
        with TempDisconnectPricingSaveHandler():
            # first pricing
            Pricing.objects.create(
                start_location=self.location_1,
                end_location=self.location_2,
                price_base=500000000
            )
            # pricing with different route
            Pricing.objects.create(
                start_location=self.location_3,
                end_location=self.location_2,
                price_base=250000000
            )
            # pricing with reverse route then pricing 1
            Pricing.objects.create(
                start_location=self.location_2,
                end_location=self.location_1,
                price_base=350000000
            )

    def test_create_pricing_no_2nd_bidirectional_allowed(self):
        with TempDisconnectPricingSaveHandler():
            Pricing.objects.create(
                start_location=self.location_1,
                end_location=self.location_2,
                price_base=500000000,
                is_bidirectional=True
            )
            p = Pricing.objects.create(
                start_location=self.location_2,
                end_location=self.location_1,
                price_base=500000000,
                is_bidirectional=True
            )
            with self.assertRaises(ValidationError):
                p.clean()

    def test_create_pricing_no_2nd_unidirectional_allowed(self):
        with TempDisconnectPricingSaveHandler():
            Pricing.objects.create(
                start_location=self.location_1,
                end_location=self.location_2,
                price_base=500000000,
                is_bidirectional=True
            )
            p = Pricing.objects.create(
                start_location=self.location_2,
                end_location=self.location_1,
                price_base=500000000,
                is_bidirectional=False
            )
            p.clean()
            # this test case has been temporary inverted to allow users
            # to migrate their pricings
            """
            with self.assertRaises(ValidationError):
                p.clean()
            """
            
    def test_create_pricing_2nd_must_be_unidirectional_a(self):
        with TempDisconnectPricingSaveHandler():
            Pricing.objects.create(
                start_location=self.location_1,
                end_location=self.location_2,
                price_base=500000000,
                is_bidirectional=False
            )
            p = Pricing.objects.create(
                start_location=self.location_2,
                end_location=self.location_1,
                price_base=500000000,
                is_bidirectional=True
            )
            with self.assertRaises(ValidationError):
                p.clean()
    
    def test_create_pricing_2nd_ok_when_unidirectional(self):
        with TempDisconnectPricingSaveHandler():
            Pricing.objects.create(
                start_location=self.location_1,
                end_location=self.location_2,
                price_base=500000000,
                is_bidirectional=False
            )
            p = Pricing.objects.create(
                start_location=self.location_2,
                end_location=self.location_1,
                price_base=500000000,
                is_bidirectional=False
            )       
            p.clean()

    @patch(MODULE_PATH + '.FREIGHT_FULL_ROUTE_NAMES', False)
    def test_name_short(self):        
        p = Pricing(
            start_location=self.location_1,
            end_location=self.location_2,
            price_base=50000000
        )
        self.assertEqual(
            p.name,
            'Jita <-> Amamake'
        )

    @patch(MODULE_PATH + '.FREIGHT_FULL_ROUTE_NAMES', True)
    def test_name_full(self):        
        p = Pricing(
            start_location=self.location_1,
            end_location=self.location_2,
            price_base=50000000
        )
        self.assertEqual(
            p.name,            
            'Jita IV - Moon 4 - Caldari Navy Assembly Plant <-> ' 
            'Amamake - 3 Time Nearly AT Winners'
        )

    def test_name_uni_directional(self):
        p = Pricing(
            start_location=self.location_1,
            end_location=self.location_2,
            price_base=50000000,
            is_bidirectional=False
        )
        self.assertEqual(
            p.name,
            'Jita -> Amamake'
        )

    def test_get_calculated_price(self):
        p = Pricing()
        p.price_per_volume = 50
        self.assertEqual(
            p.get_calculated_price(10, 0), 
            500
        )

        p = Pricing()        
        p.price_per_collateral_percent = 2
        self.assertEqual(
            p.get_calculated_price(10, 1000), 
            20
        )

        p = Pricing()        
        p.price_per_volume = 50
        p.price_per_collateral_percent = 2
        self.assertEqual(
            p.get_calculated_price(10, 1000), 
            520
        )

        p = Pricing()
        p.price_base = 20
        self.assertEqual(
            p.get_calculated_price(10, 1000), 
            20
        )

        p = Pricing()
        p.price_min = 1000
        self.assertEqual(
            p.get_calculated_price(10, 1000), 
            1000
        )

        p = Pricing()
        p.price_base = 20
        p.price_per_volume = 50
        self.assertEqual(
            p.get_calculated_price(10, 1000), 
            520
        )

        p = Pricing()
        p.price_base = 20
        p.price_per_volume = 50
        p.price_min = 1000
        self.assertEqual(
            p.get_calculated_price(10, 1000), 
            1000
        )

        p = Pricing()
        p.price_base = 20
        p.price_per_volume = 50
        p.price_per_collateral_percent = 2
        p.price_min = 500
        self.assertEqual(
            p.get_calculated_price(10, 1000), 
            540
        )

        with self.assertRaises(ValueError):            
            p.get_calculated_price(-5, 0)

        with self.assertRaises(ValueError):            
            p.get_calculated_price(50, -5)

        p = Pricing()
        p.price_base = 0    
        self.assertEqual(
            p.get_calculated_price(None, None),
            0
        )

        p = Pricing()
        p.price_per_volume = 50
        self.assertEqual(
            p.get_calculated_price(10, None),
            500
        )

        p = Pricing()
        p.price_per_collateral_percent = 2
        self.assertEqual(
            p.get_calculated_price(None, 100),
            2
        )
    
    def test_get_contract_pricing_errors(self):
        p = Pricing()
        p.price_base = 50
        self.assertIsNone(p.get_contract_price_check_issues(10, 20, 50))
                
        p = Pricing()
        p.price_base = 500
        p.volume_max = 300        
        self.assertIsNotNone(p.get_contract_price_check_issues(350, 1000))

        p = Pricing()
        p.price_base = 500
        p.volume_min = 100
        self.assertIsNotNone(p.get_contract_price_check_issues(50, 1000))

        p = Pricing()
        p.price_base = 500
        p.collateral_max = 300        
        self.assertIsNotNone(p.get_contract_price_check_issues(350, 1000))

        p = Pricing()
        p.price_base = 500
        p.collateral_min = 300        
        self.assertIsNotNone(p.get_contract_price_check_issues(350, 200))

        p = Pricing()
        p.price_base = 500        
        self.assertIsNotNone(p.get_contract_price_check_issues(350, 200, 400))
        
        p = Pricing()
        p.price_base = 500
        with self.assertRaises(ValueError):            
            p.get_contract_price_check_issues(-5, 0)

        with self.assertRaises(ValueError):            
            p.get_contract_price_check_issues(50, -5)

        with self.assertRaises(ValueError):            
            p.get_contract_price_check_issues(50, 5, -5)
        
    def test_collateral_min_allows_zero(self):
        p = Pricing()
        p.price_base = 500
        p.collateral_min = 0
        self.assertIsNone(p.get_contract_price_check_issues(350, 0))

    def test_collateral_min_allows_none(self):
        p = Pricing()
        p.price_base = 500        
        self.assertIsNone(p.get_contract_price_check_issues(350, 0))

    def test_zero_collateral_allowed_for_collateral_pricing(self):
        p = Pricing()        
        p.collateral_min = 0
        p.price_base = 500
        p.price_per_collateral_percent = 2
        self.assertIsNone(p.get_contract_price_check_issues(350, 0))
        self.assertEqual(
            p.get_calculated_price(350, 0),
            500
        )

    def test_price_per_volume_modifier_none_if_not_set(self):
        p = Pricing()
        self.assertIsNone(p.price_per_volume_modifier())
        self.assertIsNone(p.price_per_volume_eff())

    def test_price_per_volume_modifier_ignored_if_not_set(self):
        p = Pricing()
        p.price_per_volume = 50
        self.assertEqual(
            p.get_calculated_price(10, None),
            500
        )

    def test_price_per_volume_modifier_not_used(self):
        self.handler.price_per_volume_modifier = 10
        self.handler.save()

        p = Pricing()
        p.price_per_volume = 50

        self.assertIsNone(
            p.price_per_volume_modifier()
        )

    def test_price_per_volume_modifier_normal_calc(self):
        self.handler.price_per_volume_modifier = 10
        self.handler.save()

        p = Pricing()
        p.price_per_volume = 50
        p.use_price_per_volume_modifier = True

        self.assertEqual(
            p.price_per_volume_eff(),
            55
        )

        self.assertEqual(
            p.get_calculated_price(10, None),
            550
        )

    def test_price_per_volume_modifier_normal_calc_2(self):
        self.handler.price_per_volume_modifier = -10
        self.handler.save()

        p = Pricing()
        p.price_per_volume = 50
        p.use_price_per_volume_modifier = True

        self.assertEqual(
            p.price_per_volume_eff(),
            45
        )

        self.assertEqual(
            p.get_calculated_price(10, None),
            450
        )

    def test_price_per_volume_modifier_price_never_negative(self):
        self.handler.price_per_volume_modifier = -200
        self.handler.save()

        p = Pricing()
        p.price_per_volume = 50
        p.use_price_per_volume_modifier = True

        self.assertEqual(
            p.price_per_volume_eff(),
            0
        )

    def test_price_per_volume_modifier_no_manager(self):
        p = Pricing(price_base=50000000)
        p.use_price_per_volume_modifier = True
        self.assertIsNone(p.price_per_volume_modifier())

    def test_requires_volume(self):        
        self.assertTrue(Pricing(price_per_volume=10000).requires_volume())
        self.assertTrue(Pricing(volume_min=10000).requires_volume())
        self.assertTrue(Pricing(
            price_per_volume=10000,
            volume_min=10000
        ).requires_volume())
        self.assertFalse(Pricing().requires_volume())

    def test_requires_collateral(self):        
        self.assertTrue(
            Pricing(price_per_collateral_percent=2).requires_collateral()
        )
        self.assertTrue(
            Pricing(collateral_min=50000000).requires_collateral()
        )
        self.assertTrue(
            Pricing(
                price_per_collateral_percent=2,
                collateral_min=50000000
            ).requires_collateral()
        )
        self.assertFalse(Pricing().requires_collateral())

    def test_clean_force_error(self):
        p = Pricing()
        with self.assertRaises(ValidationError):
            p.clean()
    
    def test_is_fix_price(self):
        self.assertTrue(
            Pricing(price_base=50000000).is_fix_price()
        )
        self.assertFalse(
            Pricing(price_base=50000000, price_min=40000000).is_fix_price()
        )
        self.assertFalse(
            Pricing(price_base=50000000, price_per_volume=400).is_fix_price()
        )
        self.assertFalse(
            Pricing(price_base=50000000, price_per_collateral_percent=2)
            .is_fix_price()
        )
        self.assertFalse(Pricing().is_fix_price())

    def test_clean_normal(self):
        p = Pricing(price_base=50000000)        
        p.clean()


class TestContract(NoSocketsTestCase):
    
    def setUp(self):

        for character in characters_data:
            EveCharacter.objects.create(**character)
            EveCorporationInfo.objects.get_or_create(
                corporation_id=character['corporation_id'],
                defaults={
                    'corporation_name': character['corporation_name'],
                    'corporation_ticker': character['corporation_ticker'],
                    'member_count': 42
                }
            )
        
        # 1 user
        self.character = EveCharacter.objects.get(character_id=90000001)
        self.corporation = EveCorporationInfo.objects.get(
            corporation_id=self.character.corporation_id
        )
        
        self.organization = EveEntity.objects.create(
            id=self.character.alliance_id,
            category=EveEntity.CATEGORY_ALLIANCE,
            name=self.character.alliance_name
        )
        
        self.user = User.objects.create_user(
            self.character.character_name,
            'abc@example.com',
            'password'
        )

        self.main_ownership = CharacterOwnership.objects.create(
            character=self.character,
            owner_hash='x1',
            user=self.user
        )        

        # Locations
        self.location_1 = Location.objects.create(
            id=60003760,
            name='Jita IV - Moon 4 - Caldari Navy Assembly Plant',
            solar_system_id=30000142,
            type_id=52678,
            category_id=3
        )
        self.location_2 = Location.objects.create(
            id=1022167642188,
            name='Amamake - 3 Time Nearly AT Winners',
            solar_system_id=30002537,
            type_id=35834,
            category_id=65
        )      

        # create contracts
        with TempDisconnectPricingSaveHandler():
            self.pricing = Pricing.objects.create(
                start_location=self.location_1,
                end_location=self.location_2,
                price_base=500000000
            )
        
        self.handler = ContractHandler.objects.create(
            organization=self.organization,
            character=self.main_ownership            
        )
        self.contract = Contract.objects.create(
            handler=self.handler,
            contract_id=1,
            collateral=0,
            date_issued=now(),
            date_expired=now() + timedelta(days=5),
            days_to_complete=3,
            end_location=self.location_2,
            for_corporation=False,
            issuer_corporation=self.corporation,
            issuer=self.character,
            reward=50000000,
            start_location=self.location_1,
            status=Contract.STATUS_OUTSTANDING,
            volume=50000,
            pricing=self.pricing
        )
    
    def test_hours_issued_2_completed(self):
        self.contract.date_completed = \
            self.contract.date_issued + timedelta(hours=9)

        self.assertEqual(
            self.contract.hours_issued_2_completed,
            9
        )

        self.contract.date_completed = None
        self.assertIsNone(self.contract.hours_issued_2_completed)
            
    def test_str(self):
        self.assertEqual(
            str(self.contract),
            '1: Jita -> Amamake'
        )

    def test_date_latest(self):
        # initial contract only had date_issued
        self.assertEqual(
            self.contract.date_issued, 
            self.contract.date_latest
        )

        # adding date_accepted to contract
        self.contract.date_accepted = \
            self.contract.date_issued + timedelta(days=1)
        self.assertEqual(
            self.contract.date_accepted, 
            self.contract.date_latest
        )

        # adding date_completed to contract
        self.contract.date_completed = \
            self.contract.date_accepted + timedelta(days=1)
        self.assertEqual(
            self.contract.date_completed, 
            self.contract.date_latest
        )

    @patch(MODULE_PATH + '.FREIGHT_HOURS_UNTIL_STALE_STATUS', 24)
    def test_has_stale_status(self):
        # initial contract only had date_issued
        # date_issued is now
        self.assertFalse(self.contract.has_stale_status)

        # date_issued is 30 hours ago
        self.contract.date_issued = \
            self.contract.date_issued - timedelta(hours=30)
        self.assertTrue(self.contract.has_stale_status)

    def test_acceptor_name(self):
        
        contract = self.contract        
        self.assertIsNone(contract.acceptor_name)

        contract.acceptor_corporation = self.corporation
        self.assertEqual(
            contract.acceptor_name,
            self.corporation.corporation_name
        )
        
        contract.acceptor = self.character
        self.assertEqual(
            contract.acceptor_name,
            self.character.character_name
        )

    def test_get_issues_list(self):
        self.assertListEqual(
            self.contract.get_issue_list(),
            []
        )
        self.contract.issues = '["one", "two"]'
        self.assertListEqual(
            self.contract.get_issue_list(),
            ["one", "two"]
        )

    def test_generate_embed_w_pricing(self):
        x = self.contract._generate_embed()
        self.assertIsInstance(x, Embed)
        self.assertEqual(x.color, Contract.EMBED_COLOR_PASSED)

    def test_generate_embed_w_pricing_issues(self):
        self.contract.issues = ['we have issues']
        x = self.contract._generate_embed()
        self.assertIsInstance(x, Embed)
        self.assertEqual(x.color, Contract.EMBED_COLOR_FAILED)

    def test_generate_embed_wo_pricing(self):
        self.contract.pricing = None
        x = self.contract._generate_embed()
        self.assertIsInstance(x, Embed)
    
    @patch(MODULE_PATH + '.FREIGHT_DISCORD_WEBHOOK_URL', 'url')
    @patch(MODULE_PATH + '.FREIGHT_DISCORD_DISABLE_BRANDING', False)
    @patch(MODULE_PATH + '.FREIGHT_DISCORD_MENTIONS', None)
    @patch(MODULE_PATH + '.Webhook.execute', autospec=True)
    def test_send_pilot_notification_normal_1(self, mock_webhook_execute):
        self.contract.send_pilot_notification()
        self.assertEqual(mock_webhook_execute.call_count, 1)

    @patch(MODULE_PATH + '.FREIGHT_DISCORD_WEBHOOK_URL', None)
    @patch(MODULE_PATH + '.Webhook.execute', autospec=True)
    def test_send_pilot_notification_no_webhook(self, mock_webhook_execute):
        self.contract.send_pilot_notification()
        self.assertEqual(mock_webhook_execute.call_count, 0)

    @patch(MODULE_PATH + '.FREIGHT_DISCORD_WEBHOOK_URL', 'url')
    @patch(MODULE_PATH + '.FREIGHT_DISCORD_DISABLE_BRANDING', True)    
    @patch(MODULE_PATH + '.Webhook.execute', autospec=True)
    @patch(MODULE_PATH + '.FREIGHT_DISCORD_MENTIONS', None)
    def test_send_pilot_notification_normal_2(self, mock_webhook_execute):
        self.contract.send_pilot_notification()
        self.assertEqual(mock_webhook_execute.call_count, 1)

    @patch(MODULE_PATH + '.FREIGHT_DISCORD_WEBHOOK_URL', 'url')
    @patch(MODULE_PATH + '.FREIGHT_DISCORD_DISABLE_BRANDING', True)    
    @patch(MODULE_PATH + '.Webhook.execute', autospec=True)
    @patch(MODULE_PATH + '.FREIGHT_DISCORD_MENTIONS', '@here')
    def test_send_pilot_notification_normal_3(self, mock_webhook_execute):
        self.contract.send_pilot_notification()
        self.assertEqual(mock_webhook_execute.call_count, 1)


class TestLocation(NoSocketsTestCase):

    def setUp(self):
        self.location = Location.objects.create(
            id=60003760,
            name='Jita IV - Moon 4 - Caldari Navy Assembly Plant',
            solar_system_id=30000142,
            type_id=52678,
            category_id=3
        )

    def test_str(self):
        self.assertEqual(
            str(self.location.name), 
            'Jita IV - Moon 4 - Caldari Navy Assembly Plant'
        )

    def test_category(self):
        self.assertEqual(self.location.category, Location.CATEGORY_STATION_ID)

    def test_solar_system_name(self):
        self.assertEqual(self.location.solar_system_name, 'Jita')


class TestContractHandler(NoSocketsTestCase):
    
    def setUp(self):
        for character in characters_data:
            EveCharacter.objects.create(**character)
            EveCorporationInfo.objects.get_or_create(
                corporation_id=character['corporation_id'],
                defaults={
                    'corporation_name': character['corporation_name'],
                    'corporation_ticker': character['corporation_ticker'],
                    'member_count': 42
                }
            )
        
        # 1 user
        self.character = EveCharacter.objects.get(character_id=90000001)
        self.corporation = EveCorporationInfo.objects.get(
            corporation_id=self.character.corporation_id
        )
        
        self.organization = EveEntity.objects.create(
            id=self.character.alliance_id,
            category=EveEntity.CATEGORY_ALLIANCE,
            name=self.character.alliance_name
        )
        
        self.user = User.objects.create_user(
            self.character.character_name,
            'abc@example.com',
            'password'
        )

        self.main_ownership = CharacterOwnership.objects.create(
            character=self.character,
            owner_hash='x1',
            user=self.user
        )       

        self.handler = ContractHandler.objects.create(
            organization=self.organization,
            character=self.main_ownership            
        )

    def test_str(self):
        self.assertEqual(str(self.handler), 'Justice League')

    def test_repr(self):        
        expected = 'ContractHandler(pk={}, organization=\'Justice League\')'\
            .format(self.handler.pk)   
        self.assertEqual(repr(self.handler), expected)

    def test_operation_mode_friendly(self):
        self.handler.operation_mode = FREIGHT_OPERATION_MODE_MY_ALLIANCE
        self.assertEqual(
            self.handler.operation_mode_friendly, 
            'My Alliance'
        )
        self.handler.operation_mode = 'undefined operation mode'
        with self.assertRaises(ValueError):
            self.handler.operation_mode_friendly

    def test_get_availability_text_for_contracts(self):
        self.handler.operation_mode = FREIGHT_OPERATION_MODE_MY_ALLIANCE
        self.assertEqual(
            self.handler.get_availability_text_for_contracts(),
            'Private (Justice League) [My Alliance]'
        )
        self.handler.operation_mode = FREIGHT_OPERATION_MODE_MY_CORPORATION
        self.assertEqual(
            self.handler.get_availability_text_for_contracts(),
            'Private (Justice League) [My Corporation]'
        )
        self.handler.operation_mode = FREIGHT_OPERATION_MODE_CORP_PUBLIC
        self.assertEqual(
            self.handler.get_availability_text_for_contracts(),
            'Private (Justice League) '
        )

    @patch(MODULE_PATH + '.FREIGHT_CONTRACT_SYNC_GRACE_MINUTES', 30)
    def test_is_sync_ok(self):        
        # no errors and recent sync
        self.handler.last_error = ContractHandler.ERROR_NONE
        self.handler.last_sync = now()
        self.assertTrue(self.handler.is_sync_ok)

        # no errors and sync within grace period
        self.handler.last_error = ContractHandler.ERROR_NONE
        self.handler.last_sync = now() - timedelta(minutes=29)
        self.assertTrue(self.handler.is_sync_ok)

        # recent sync error 
        self.handler.last_error = \
            ContractHandler.ERROR_INSUFFICIENT_PERMISSIONS
        self.handler.last_sync = now()
        self.assertFalse(self.handler.is_sync_ok)
        
        # no error, but no sync within grace period
        self.handler.last_error = ContractHandler.ERROR_NONE
        self.handler.last_sync = now() - timedelta(minutes=31)
        self.assertFalse(self.handler.is_sync_ok)

    def test_set_sync_status_1(self):
        self.handler.last_error = ContractHandler.ERROR_UNKNOWN
        self.handler.last_sync = None
        self.handler.save()

        self.handler.set_sync_status(ContractHandler.ERROR_TOKEN_EXPIRED)
        self.assertEqual(
            self.handler.last_error, ContractHandler.ERROR_TOKEN_EXPIRED
        )
        self.assertGreater(self.handler.last_sync, now() - timedelta(minutes=1))

    def test_set_sync_status_2(self):
        self.handler.last_error = ContractHandler.ERROR_UNKNOWN
        self.handler.last_sync = None
        self.handler.save()

        self.handler.set_sync_status()
        self.assertEqual(self.handler.last_error, ContractHandler.ERROR_NONE)
        self.assertGreater(self.handler.last_sync, now() - timedelta(minutes=1))


class TestContractsSync(NoSocketsTestCase):
    
    def setUp(self):

        create_entities_from_characters()
        
        # 1 user
        self.character = EveCharacter.objects.get(character_id=90000001)
        
        self.alliance = EveEntity.objects.get(
            id=self.character.alliance_id
        )
        self.corporation = EveEntity.objects.get(
            id=self.character.corporation_id
        )
        self.user = User.objects.create_user(
            self.character.character_name,
            'abc@example.com', 'password'
        )

        self.main_ownership = CharacterOwnership.objects.create(
            character=self.character, owner_hash='x1', user=self.user
        )
        create_locations()
        
    # identify wrong operation mode
    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE', 
        FREIGHT_OPERATION_MODE_MY_CORPORATION
    )
    def test_run_wrong_operation_mode(self):
        handler = ContractHandler.objects.create(
            organization=self.alliance,
            operation_mode=FREIGHT_OPERATION_MODE_MY_ALLIANCE,
            character=self.main_ownership,
        )
        self.assertFalse(handler.update_contracts_esi())
        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, ContractHandler.ERROR_OPERATION_MODE_MISMATCH
        )

    # run without char    
    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE', 
        FREIGHT_OPERATION_MODE_MY_ALLIANCE
    )
    def test_run_no_sync_char(self):
        handler = ContractHandler.objects.create(
            organization=self.alliance,            
            operation_mode=FREIGHT_OPERATION_MODE_MY_ALLIANCE,
        )
        self.assertFalse(
            handler.update_contracts_esi()
        )
        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, ContractHandler.ERROR_NO_CHARACTER
        )

    # test expired token
    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE', 
        FREIGHT_OPERATION_MODE_MY_ALLIANCE
    )
    @patch(MODULE_PATH + '.Token')    
    def test_run_manager_sync_expired_token(self, mock_Token):        
        mock_Token.objects.filter.side_effect = TokenExpiredError()        
        AuthUtils.add_permission_to_user_by_name(
            'freight.setup_contract_handler', self.user
        )
        handler = ContractHandler.objects.create(
            organization=self.alliance,
            character=self.main_ownership,
            operation_mode=FREIGHT_OPERATION_MODE_MY_ALLIANCE,
        )
        
        # run manager sync
        self.assertFalse(handler.update_contracts_esi())

        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, ContractHandler.ERROR_TOKEN_EXPIRED            
        )

    # test invalid token
    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE', 
        FREIGHT_OPERATION_MODE_MY_ALLIANCE
    )
    @patch(MODULE_PATH + '.Token')
    def test_run_manager_sync_invalid_token(self, mock_Token):
        mock_Token.objects.filter.side_effect = TokenInvalidError()
        AuthUtils.add_permission_to_user_by_name(
            'freight.setup_contract_handler', self.user
        )
        handler = ContractHandler.objects.create(
            organization=self.alliance,
            character=self.main_ownership,
            operation_mode=FREIGHT_OPERATION_MODE_MY_ALLIANCE,
        )
        
        # run manager sync
        self.assertFalse(handler.update_contracts_esi())

        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, ContractHandler.ERROR_TOKEN_INVALID
        )

    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE', 
        FREIGHT_OPERATION_MODE_MY_ALLIANCE
    )
    @patch(MODULE_PATH + '.Token')    
    def test_run_manager_sync_no_valid_token(
        self,             
        mock_Token
    ):        
        mock_Token.objects.filter.return_value.require_scopes.return_value\
            .require_valid.return_value.first.return_value = None
        
        AuthUtils.add_permission_to_user_by_name(
            'freight.setup_contract_handler', self.user
        )        
        handler = ContractHandler.objects.create(
            organization=self.alliance,
            character=self.main_ownership,
            operation_mode=FREIGHT_OPERATION_MODE_MY_ALLIANCE,
        )
        
        # run manager sync
        self.assertFalse(handler.update_contracts_esi())

        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, ContractHandler.ERROR_TOKEN_INVALID            
        )

    # exception occuring for one of the contracts    
    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE', 
        FREIGHT_OPERATION_MODE_MY_ALLIANCE
    )
    @patch(
        MODULE_PATH + '.Contract.objects.update_or_create_from_dict'
    )
    @patch(MODULE_PATH + '.Token')    
    @patch(MODULE_PATH + '.esi_client_factory')
    def test_sync_contract_fails(
        self, 
        mock_esi_client_factory,         
        mock_Token,
        mock_Contracts_objects_update_or_create_from_dict
    ):        
        # create mocks
        def get_contracts_page(*args, **kwargs):
            """returns single page for operation.result(), first with header"""
            page_size = 2
            mock_calls_count = len(mock_operation.mock_calls)
            start = (mock_calls_count - 1) * page_size
            stop = start + page_size
            pages_count = int(math.ceil(
                len(contracts_data) / page_size
            ))
            mock_response = Mock()
            mock_response.headers = {'x-pages': pages_count}
            return [contracts_data[start:stop], mock_response]

        def func_Contracts_objects_update_or_create_from_dict(
            handler, 
            contract, 
            esi_client
        ):            
            raise RuntimeError('Test exception')
            
        mock_Contracts_objects_update_or_create_from_dict\
            .side_effect = func_Contracts_objects_update_or_create_from_dict

        mock_client = Mock()
        mock_operation = Mock()
        mock_operation.result.side_effect = get_contracts_page        
        mock_client.Contracts.get_corporations_corporation_id_contracts = Mock(
            return_value=mock_operation
        )
        mock_esi_client_factory.return_value = mock_client        

        mock_Token.objects.filter.return_value\
            .require_scopes.return_value\
            .require_valid.return_value\
            .first.return_value = Mock(spec=Token)

        AuthUtils.add_permission_to_user_by_name(
            'freight.setup_contract_handler', self.user
        )
        handler = ContractHandler.objects.create(
            organization=self.alliance,
            character=self.main_ownership,
            operation_mode=FREIGHT_OPERATION_MODE_MY_ALLIANCE
        )
        
        # run manager sync
        self.assertTrue(handler.update_contracts_esi())

        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, ContractHandler.ERROR_UNKNOWN            
        )
        
    # normal synch of new contracts, mode my_alliance
    # freight.tests.TestRunContractsSync.test_run_manager_sync_normal_my_alliance    
    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE', 
        FREIGHT_OPERATION_MODE_MY_ALLIANCE
    )
    @patch(MODULE_PATH + '.Token')    
    @patch(MODULE_PATH + '.esi_client_factory')
    def test_sync_my_alliance_contracts_only(
        self, 
        mock_esi_client_factory,         
        mock_Token
    ):        
        # create mocks
        def get_contracts_page(*args, **kwargs):
            """returns single page for operation.result(), first with header"""
            page_size = 2
            mock_calls_count = len(mock_operation.mock_calls)
            start = (mock_calls_count - 1) * page_size
            stop = start + page_size
            pages_count = int(math.ceil(len(contracts_data) / page_size))
            mock_response = Mock()
            mock_response.headers = {'x-pages': pages_count}
            return [contracts_data[start:stop], mock_response]
            
        mock_client = Mock()
        mock_operation = Mock()
        mock_operation.result.side_effect = get_contracts_page        
        mock_client.Contracts.get_corporations_corporation_id_contracts = Mock(
            return_value=mock_operation
        )
        mock_esi_client_factory.return_value = mock_client        

        mock_Token.objects.filter.return_value\
            .require_scopes.return_value\
            .require_valid.return_value\
            .first.return_value = Mock(spec=Token)

        AuthUtils.add_permission_to_user_by_name(
            'freight.setup_contract_handler', self.user
        )
        handler = ContractHandler.objects.create(
            organization=self.alliance,
            character=self.main_ownership,
            operation_mode=FREIGHT_OPERATION_MODE_MY_ALLIANCE
        )
        
        # run manager sync
        self.assertTrue(handler.update_contracts_esi())

        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, ContractHandler.ERROR_NONE            
        )
        
        # should have tried to fetch contracts
        self.assertEqual(mock_operation.result.call_count, 9)

        # should only contain the right contracts
        contract_ids = [
            x['contract_id'] 
            for x in Contract.objects
            .filter(status__exact=Contract.STATUS_OUTSTANDING)
            .values('contract_id')
        ]
        self.assertCountEqual(
            contract_ids,
            [149409005, 149409014, 149409006, 149409015]
        )

    # normal synch of new contracts, mode my_corporation
    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE',
        FREIGHT_OPERATION_MODE_MY_CORPORATION
    )
    @patch(MODULE_PATH + '.Token')    
    @patch(MODULE_PATH + '.esi_client_factory')
    def test_sync_my_corporation_contracts_only(
        self, 
        mock_esi_client_factory,         
        mock_Token
    ):
        # create mocks
        def get_contracts_page(*args, **kwargs):
            """returns single page for operation.result(), first with header"""
            page_size = 2
            mock_calls_count = len(mock_operation.mock_calls)
            start = (mock_calls_count - 1) * page_size
            stop = start + page_size
            pages_count = int(math.ceil(len(contracts_data) / page_size))
            mock_response = Mock()
            mock_response.headers = {'x-pages': pages_count}
            return [contracts_data[start:stop], mock_response]
        
        mock_client = Mock()
        mock_operation = Mock()
        mock_operation.result.side_effect = get_contracts_page        
        mock_client.Contracts.get_corporations_corporation_id_contracts = Mock(
            return_value=mock_operation
        )
        mock_esi_client_factory.return_value = mock_client        

        mock_Token.objects.filter.return_value\
            .require_scopes.return_value\
            .require_valid.return_value\
            .first.return_value = Mock(spec=Token)

        AuthUtils.add_permission_to_user_by_name(
            'freight.setup_contract_handler', self.user
        )
        handler = ContractHandler.objects.create(
            organization=self.corporation,
            character=self.main_ownership,
            operation_mode=FREIGHT_OPERATION_MODE_MY_CORPORATION
        )
        
        # run manager sync
        self.assertTrue(handler.update_contracts_esi())

        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, ContractHandler.ERROR_NONE
        )
        
        # should have tried to fetch contracts
        self.assertEqual(mock_operation.result.call_count, 9)
        
        # should only contain the right contracts
        contract_ids = [
            x['contract_id'] 
            for x in Contract.objects
            .filter(status__exact=Contract.STATUS_OUTSTANDING)
            .values('contract_id')
        ]
        self.assertCountEqual(
            contract_ids,
            [
                149409016, 
                149409061, 
                149409062,
                149409063, 
                149409064, 
            ]
        )

    # normal synch of new contracts, mode my_corporation
    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE', 
        FREIGHT_OPERATION_MODE_CORP_IN_ALLIANCE
    )
    @patch(MODULE_PATH + '.Token')    
    @patch(MODULE_PATH + '.esi_client_factory')
    def test_sync_corp_in_alliance_contracts_only(
        self, 
        mock_esi_client_factory,         
        mock_Token
    ):
        # create mocks
        def get_contracts_page(*args, **kwargs):
            """returns single page for operation.result(), first with header"""
            page_size = 2
            mock_calls_count = len(mock_operation.mock_calls)
            start = (mock_calls_count - 1) * page_size
            stop = start + page_size
            pages_count = int(math.ceil(len(contracts_data) / page_size))
            mock_response = Mock()
            mock_response.headers = {'x-pages': pages_count}
            return [contracts_data[start:stop], mock_response]
        
        mock_client = Mock()
        mock_operation = Mock()
        mock_operation.result.side_effect = get_contracts_page        
        mock_client.Contracts.get_corporations_corporation_id_contracts = Mock(
            return_value=mock_operation
        )
        mock_esi_client_factory.return_value = mock_client        

        mock_Token.objects.filter.return_value\
            .require_scopes.return_value\
            .require_valid.return_value\
            .first.return_value = Mock(spec=Token)    

        AuthUtils.add_permission_to_user_by_name(
            'freight.setup_contract_handler', self.user
        )
        handler = ContractHandler.objects.create(
            organization=self.corporation,
            character=self.main_ownership,
            operation_mode=FREIGHT_OPERATION_MODE_CORP_IN_ALLIANCE
        )
        
        # run manager sync
        self.assertTrue(handler.update_contracts_esi())

        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, ContractHandler.ERROR_NONE            
        )
        
        # should have tried to fetch contracts
        self.assertEqual(mock_operation.result.call_count, 9)

        # should only contain the right contracts
        contract_ids = [
            x['contract_id'] 
            for x in Contract.objects
            .filter(status__exact=Contract.STATUS_OUTSTANDING)
            .values('contract_id')
        ]
        self.assertCountEqual(
            contract_ids,
            [
                149409016, 
                149409017, 
                149409061, 
                149409062,
                149409063, 
                149409064, 
            ]
        )

    # normal synch of new contracts, mode corp_public
    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE', 
        FREIGHT_OPERATION_MODE_CORP_PUBLIC
    )    
    @patch(MODULE_PATH + '.Token')
    @patch(
        'freight.managers.EveCorporationInfo.objects.create_corporation', 
        side_effect=ObjectNotFound(9999999, 'corporation')
    )
    @patch(
        'freight.managers.EveCharacter.objects.create_character', 
        side_effect=ObjectNotFound(9999999, 'character')
    )    
    @patch(MODULE_PATH + '.esi_client_factory')
    def test_sync_corp_public_contracts_only(
        self, 
        mock_esi_client_factory,         
        mock_EveCharacter_objects_create_character,
        mock_EveCorporationInfo_objects_create_corporation,
        mock_Token
    ):
        # create mocks
        def get_contracts_page(*args, **kwargs):
            """returns single page for operation.result(), first with header"""
            page_size = 2
            mock_calls_count = len(mock_operation.mock_calls)
            start = (mock_calls_count - 1) * page_size
            stop = start + page_size
            pages_count = int(math.ceil(len(contracts_data) / page_size))
            mock_response = Mock()
            mock_response.headers = {'x-pages': pages_count}
            return [contracts_data[start:stop], mock_response]
        
        mock_client = Mock()
        mock_operation = Mock()
        mock_operation.result.side_effect = get_contracts_page        
        mock_client.Contracts.get_corporations_corporation_id_contracts = Mock(
            return_value=mock_operation
        )
        mock_esi_client_factory.return_value = mock_client        

        mock_Token.objects.filter.return_value\
            .require_scopes.return_value\
            .require_valid.return_value\
            .first.return_value = Mock(spec=Token)  

        AuthUtils.add_permission_to_user_by_name(
            'freight.setup_contract_handler', self.user
        )
        handler = ContractHandler.objects.create(
            organization=self.corporation,
            character=self.main_ownership,
            operation_mode=FREIGHT_OPERATION_MODE_CORP_PUBLIC
        )
        
        # run manager sync
        self.assertTrue(handler.update_contracts_esi())

        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, ContractHandler.ERROR_NONE
        )
        
        # should have tried to fetch contracts
        self.assertEqual(mock_operation.result.call_count, 9)

        # should only contain the right contracts
        contract_ids = [
            x['contract_id'] 
            for x in Contract.objects
            .filter(status__exact=Contract.STATUS_OUTSTANDING)
            .values('contract_id')
        ]
        self.assertCountEqual(
            contract_ids,
            [
                149409016, 
                149409061, 
                149409062, 
                149409063, 
                149409064, 
                149409017, 
                149409018
            ]
        )
        
    def test_operation_mode_friendly(self):
        handler = ContractHandler.objects.create(
            organization=self.alliance,
            operation_mode=FREIGHT_OPERATION_MODE_MY_ALLIANCE,
            character=self.main_ownership,
        )
        self.assertEqual(
            handler.operation_mode_friendly, FREIGHT_OPERATION_MODES[0][1]
        )

        handler.operation_mode = FREIGHT_OPERATION_MODE_MY_CORPORATION
        self.assertEqual(
            handler.operation_mode_friendly, FREIGHT_OPERATION_MODES[1][1]
        )

        handler.operation_mode = FREIGHT_OPERATION_MODE_CORP_IN_ALLIANCE
        self.assertEqual(
            handler.operation_mode_friendly, FREIGHT_OPERATION_MODES[2][1]
        )

        handler.operation_mode = FREIGHT_OPERATION_MODE_CORP_PUBLIC
        self.assertEqual(
            handler.operation_mode_friendly, FREIGHT_OPERATION_MODES[3][1]
        )

    def test_last_error_message_friendly(self):
        handler = ContractHandler.objects.create(
            organization=self.alliance,
            operation_mode=FREIGHT_OPERATION_MODE_MY_ALLIANCE,
            character=self.main_ownership,
            last_error=ContractHandler.ERROR_UNKNOWN
        )
        self.assertEqual(
            handler.last_error_message_friendly, 
            ContractHandler.ERRORS_LIST[7][1]
        )

    """
    # freight.tests.TestRunContractsSync.test_statistics_calculation
    @patch(
        MODULE_PATH + '.FREIGHT_OPERATION_MODE', 
        FREIGHT_OPERATION_MODE_CORP_IN_ALLIANCE
    )    
    @patch(MODULE_PATH + '.esi_client_factory')
    def test_statistics_calculation(
            self, 
            mock_esi_client_factory,             
        ):
        # create mocks
        def get_contracts_page(*args, **kwargs):
            #returns single page for operation.result(), first with header
            page_size = 2
            mock_calls_count = len(mock_operation.mock_calls)
            start = (mock_calls_count - 1) * page_size
            stop = start + page_size
            pages_count = int(math.ceil(len(contracts_data) / page_size))
            if mock_calls_count == 1:
                mock_response = Mock()
                mock_response.headers = {'x-pages': pages_count}
                return [contracts_data[start:stop], mock_response]
            else:
                return contracts_data[start:stop]
        
        mock_client = Mock()
        mock_operation = Mock()
        mock_operation.result.side_effect = get_contracts_page        
        mock_client.Contracts.get_corporations_corporation_id_contracts = Mock(
            return_value=mock_operation
        )
        mock_esi_client_factory.return_value = mock_client                

        # create test data
        p = Permission.objects.filter(codename='basic_access').first()
        self.user.user_permissions.add(p)
        p = Permission.objects.filter(codename='setup_contract_handler').first()
        self.user.user_permissions.add(p)
        p = Permission.objects.filter(codename='view_contract').first()
        self.user.user_permissions.add(p)

        self.user.save()
        handler = ContractHandler.objects.create(
            organization=self.corporation,
            character=self.main_ownership,
            operation_mode=FREIGHT_OPERATION_MODE_CORP_IN_ALLIANCE
        )
        
        # run manager sync
        self.assertTrue(
            handler.update_contracts_esi()
        )

        handler.refresh_from_db()
        self.assertEqual(
            handler.last_error, 
            ContractHandler.ERROR_NONE            
        )
        
        result = self.client.login(
            username=self.character.character_name, 
            password='password'
        )

        response = self.client.get(reverse('freight:index'))
        
        print('hi')
    """
