# Freight for Alliance Auth

This is a plugin app for [Alliance Auth](https://gitlab.com/allianceauth/allianceauth) (AA) that adds an alliance Freight service.

![License](https://img.shields.io/badge/license-MIT-green) ![python](https://img.shields.io/badge/python-3.5-informational) ![django](https://img.shields.io/badge/django-2.2-informational)

## Overview

This app support running a central freight service for an alliance. The main concept of such a freight service is as follows:

- Every alliance member can create courier contracts to the alliance for defined routes

- Courier contracts have a reward according to the official pricing for that route and sufficient collateral to prevent scamming

- Every interested alliance member can pick up and deliver existing courier contracts

## Features

To support this concept Alliance Freight offers the following main features:

- A calculator, so alliance members can easily calculate the reward for their current courier contract

- A current list of all outstanding courier contracts incl. an indicator showing if the contract is compliant to the pricing for that route

- Multiple routes can be defined, each with its own pricing

- Automatic notification to a Discord channel about new courier contracts

## Installation

### 1. Install app

Install into AA virtual environment with PIP install from this repo:

```bash
pip install git+https://gitlab.com/ErikKalkoken/aa-freight.git
```

### 2 Update Eve Online app

Update the Eve Online app used for authentication in your AA installation to include the following scopes:

```plain
esi-universe.read_structures.v1
esi-contracts.read_corporation_contracts.v1
```

### 3. Configure AA settings

Configure your AA settings (`local.py`) as follows:

- Add `'freight'` to `INSTALLED_APPS`
- Add these lines add to bottom of your settings file:

   ```python
   # settings for standingssync
   CELERYBEAT_SCHEDULE['freight_run_contracts_sync'] = {
       'task': 'freight.tasks.run_contracts_sync',
       'schedule': crontab(minute=0, minutes='*/10')
   }
   ```

If you want to setup notifications for Discord you can now also add the required settings. Check out section **Settings** for details.

### 4. Finalize installation into AA

Run migrations & copy static files

```bash
python manage.py migrate
python manage.py collectstatic
```

Restart your supervisor services for AA

### 5. Setup permissions

Now you can access Alliance Auth and setup permissions for your users. See section **Permissions** below for details.

### 6. Setup contract handler

Finally you need to set the contract handler with the alliance character that will be used for fetching the alliance contracts and related structures. Just click on "Set Contract Handler" and add the requested token. Note that only users with the appropriate permission will be able to see and use this function.

Once a contract handler is set the app will start fetching alliance contracts. Wait a minute and then reload the contract list page to see the result.

### 7. Define pricing

Finally go ahead and define the first pricing of a courier route. See section **Pricing** for details.

That's it. The Alliance Freight app is fully installed and ready to be used.

## Settings

Here is a list of available settings for this app. They can be configured by adding them to your AA settings file (`local.py`). If they are not set the defaults are used.

Name | Description | Default
-- | -- | --
`FREIGHT_DISCORD_WEBHOOK_URL`| Webhook URL for the Discord channel where contract notifications should appear | Not defined
`FREIGHT_DISCORD_AVATAR_URL`| URL to an image file to override the default avatar on Discord notifications, which is the Eve alliance logo | Not defined

## Permissions

This is an overview of all permissions used by this app:

Name | Purpose | Code
-- | -- | --
Can add / update locations | User can add and update Eve Online contract locations, e.g. stations and upwell structures |  `add_location`
Can access this app |Enabling the app for a user. This permission should be enabled for everyone who is allowed to use the app (e.g. Member state) |  `basic_access`
Can setup contract handler | Add or updates the alliance character for syncing contracts. This should be limited to users with admins / leadership privileges. |  `setup_contract_handler`
Can use the calculator | Enables using the calculator page the app. This permission is usually enabled for every alliance member. |  `use_calculator`
Can view the contracts list | Enables viewing the page with all outstanding courier contracts  |  `view_contracts`

## Pricing

A pricing defines a route and the parameters for calculating the price for that route along with some additional information for the users. You can define multiple pricings if you want, but at least one pricing has to be defined for this app to work.

Pricing routes are bidirectional, so it does not matter which location is chosen as start and which as destination when creating a courier contract.

Pricings are defined in the admin section of AA, so you need staff permissions to access it.

Most parameters of a pricing are optional, but you need to define at least one of the four pricing components to create a valid pricing:

- Minimum price
- Base price
- Price per volume
- Price per collateral

> **Adding Locations**:<br>If you are creating a pricing for a new route or this is the first pricing you are creating you may need to first add the locations (stations and/or structures) to the app. The best way is add new locations is with the "Add Location" feature on the main page of the app. Alternatively you can also add locations manually in the admin section.
