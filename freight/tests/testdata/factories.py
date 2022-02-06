from ...models import Pricing


def create_pricing(update_contracts: bool = False, **kwargs) -> Pricing:
    obj = Pricing(**kwargs)
    obj.save(update_contracts=update_contracts)
    return obj
