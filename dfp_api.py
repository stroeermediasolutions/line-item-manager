from __future__ import absolute_import, print_function

import logging
from builtins import range

from googleads import ad_manager as dfp
from googleads.ad_manager import AdManagerClient as DfpClient

# Current version nb of the dfp api. In case of API update, change this version
# number. For details, see
# https://developers.google.com/ad-manager/api/deprecation
VERSION_NB = "v202502"


def get_dfp_client_for_account(path):
    
    dfp_client = DfpClient.LoadFromStorage(path)

    return dfp_client


def create_orders_buckets(dfp_client: DfpClient, orders, trafficker_id: str, advertiser_id: str) -> dict:
    orders_name = [{'name': item, 'advertiserId': advertiser_id, 'traffickerId': trafficker_id}
                   for item in orders]
    orders_json = check_create_orders(dfp_client, orders_name)
    orders_ids_dict = {item['name']: item['id'] for item in orders_json}
    return orders_ids_dict

def check_create_orders(dfp_client: DfpClient, orders, skip_existing=True) -> list:
    existing_orders = []
    if skip_existing:
        existing_orders = get_orders_by_names(dfp_client, [item['name'] for item in orders])
        existing_order_names = {item['name'] for item in existing_orders}
        orders = [item for item in orders if item['name'] not in existing_order_names]

    results = []
    if orders:
        srv = dfp_client.GetService('OrderService', version=VERSION_NB)
        try:
            results = srv.createOrders(orders)
        except Exception as e:
            order_names = [o['name'] for o in orders]
            if "UniqueError.NOT_UNIQUE" in str(e.args):
                raise Exception(
                    "One or more of the names ({}) chosen for order isn't unique.".format(order_names))
            elif "TypeError.INVALID_TYPE @ [0].advertiser" in str(e.args):
                raise Exception(
                    "The company supposed to be associated with "
                    "the orders ({}) does not feature a suitable type.".format(order_names)
                )
            else:
                raise e

    return results + existing_orders

def get_orders_by_names(dfp_client: DfpClient, names):
    if not names:
        return []
    order_service = dfp_client.GetService('OrderService', version=VERSION_NB)
    query = "WHERE name IN ({})".format(', '.join(["'{}'".format(name) for name in names]))
    statement = dfp.FilterStatement(query)
    response = order_service.getOrdersByStatement(statement.ToStatement())
    if "results" not in response:
        return []
    return response["results"]



def get_bucket_key(dfp_client: DfpClient, key_name, key_type='PREDEFINED'):
    try:
        key_id = _get_key_id(dfp_client, key_name)
    except:
        key_id = create_targeting_key(dfp_client, key_name, key_type)
    return key_id

def check_bucket_key(dfp_client: DfpClient, key_name):
    try:
        key_id = _get_key_id(dfp_client, key_name)
    except:
        logging.error("Could not find key {} for DFP account {}".format(key_name, dfp_client.network_code))
        exit(1)
    return key_id

def _get_key_id(dfp_client: DfpClient, key_name):
    cts = dfp_client.GetService("CustomTargetingService", version=VERSION_NB)
    # retrieve key_id
    stmt_key = "WHERE name = :name"
    values = [{
        "key": "name",
        "value": {
            "xsi_type": "TextValue",
            "value": key_name
        }
    }
    ]
    statement_key = dfp.FilterStatement(stmt_key, values)
    try:
        key_id = cts.getCustomTargetingKeysByStatement(
            statement_key.ToStatement())["results"][0]["id"]
    except (AttributeError, KeyError, IndexError) as e:
        raise Exception(
            "Could not find key {} for DFP account {}. Please create the key in the DFP Account".format(key_name, dfp_client.network_code)
        )
    return key_id


def create_targeting_key(dfp_client: DfpClient, name, type_='FREEFORM'):
    """
    Creates a targeting key with the given name and type.
    Make sure to turn on 'report on values' manually since it cannot be set through the API.
    :param dfp_client: (googleads.dfp.DfpClient) Client for API call
    :param name: name of the targeting key
    :param type_: type is either `FREEFORM` or `PREDEFINED`
    :return: the id of the created key
    """
    cts = dfp_client.GetService("CustomTargetingService", version=VERSION_NB)
    values = [{'displayName': name, 'name': name,
               'type': type_}]
    result = cts.createCustomTargetingKeys(values)
    key_id = result[0]["id"]
    return key_id



def create_hb_key_values(dfp_client: DfpClient, values, key_id, key_name, return_all=False):
    results = create_key_values(dfp_client, key_id, values, key_name, return_all)
    return results


def create_key_values(dfp_client: DfpClient, key_id, values, key_name, return_all=False):
    key_values = [{
        "customTargetingKeyId": key_id,
        "displayName": "{:.2f}".format(value / 100),
        "name": "{:.2f}".format(value / 100),
        "matchType": "EXACT"
    } for value in values]

    return check_create_key_values(dfp_client, key_values, key_name, return_all, skip_existing=True)

def check_create_key_values(dfp_client: DfpClient, values, key_name, return_all=False, skip_existing=True, str_values=False):
    existing_values = []
    key_values = None
    if skip_existing:
        existing_values = get_all_key_values(dfp_client, key_name, only_active=True, as_dict=False)
        existing_key_values_names = {item['name'] for item in existing_values}
        key_values = [item for item in values if item['name'] not in existing_key_values_names]
    results = []
    if key_values:
        srv = dfp_client.GetService("CustomTargetingService", version=VERSION_NB)
        try:
            results = srv.createCustomTargetingValues(key_values)
        except Exception as e:
            key_names = [kn['name'] for kn in key_values]
            if "CustomTargetingError.VALUE_NAME_DUPLICATE" in str(e.args):
                pass
    if return_all:
        return results + existing_values
    elif str_values:
        values = [value['name'] for value in values]
        return get_amazon_key_value_by_name(dfp_client, key_name, values)
    else:
        values = [value['name'] for value in values]
        return get_key_value_by_name(dfp_client, key_name, values)



def get_all_key_values(dfp_client: DfpClient, key_name, only_active=True, as_dict=False):
    key_id = _get_key_id(dfp_client, key_name)
    cts = dfp_client.GetService("CustomTargetingService", version=VERSION_NB)

    # check for existing keys
    stmt_values = "WHERE customTargetingKeyId = :id "
    if only_active:
        stmt_values += "AND status = 'ACTIVE'"
    values = [{
        "key": "id",
        "value": {
            "xsi_type": "NumberValue",
            "value": key_id
        }
    }]
    statement_values = dfp.FilterStatement(stmt_values, values)
    statement_values.limit = 5000
    results = []
    while True:
        res = cts.getCustomTargetingValuesByStatement(
            statement_values.ToStatement()
        )
        if res['totalResultSetSize']:
            results.extend(res['results'])
            statement_values.offset = len(results)
        if statement_values.offset >= res['totalResultSetSize']:
            break
    if as_dict:
        results = [{key: getattr(r, key) for key in dir(r) if not key.startswith('_')} for r in results]
    return results


def get_amazon_key_value_by_name(dfp_client: DfpClient, key_name, values):
    service = dfp_client.GetService('CustomTargetingService', version=VERSION_NB)
    query = "WHERE name = '{}'".format(key_name)
    statement = dfp.FilterStatement(query)
    key_id = get_all_results_by_statement(service.getCustomTargetingKeysByStatement, statement)[0]['id']
    query = "WHERE customTargetingKeyId = '{}' AND name in ('{}')".format(key_id, "','".join(values))
    statement = dfp.FilterStatement(query)

    return get_all_results_by_statement(service.getCustomTargetingValuesByStatement, statement)

def get_key_value_by_name(dfp_client: DfpClient, key_name, values):
    service = dfp_client.GetService('CustomTargetingService', version=VERSION_NB)
    query = "WHERE name = '{}'".format(key_name)
    statement = dfp.FilterStatement(query)
    key_id = get_all_results_by_statement(service.getCustomTargetingKeysByStatement, statement)[0]['id']
    query = "WHERE customTargetingKeyId = '{}' AND name in ({})".format(key_id, ', '.join([value for value in values]))
    statement = dfp.FilterStatement(query)

    return get_all_results_by_statement(service.getCustomTargetingValuesByStatement, statement)


def get_all_results_by_statement(api_fun, statement, limit=500, as_dict=False):
    """
    This function calls a dfp api function to collect all items and return the full list of response objects.
    It performs the bulk fetching which is suggested for large data sets.
    :param api_fun: the api service function to be called
    :param statement: the statement to be used for the function call
    :return: list of all result objects
    """
    statement.limit = limit
    results = []
    while True:
        res = api_fun(statement.ToStatement()
                      )
        if res['totalResultSetSize']:
            results.extend(res['results'])
            statement.offset = len(results)
        if statement.offset >= res['totalResultSetSize']:
            break
    if as_dict:
        results = [{key: getattr(r, key) for key in dir(r) if not key.startswith('_')} for r in results]
    return results

def composing_key_values_dictionary(orders, name_prefix, orders_dict, key_values):
    values_ids = {value['name']: value['id'] for value in key_values}
    line_items_dict = dict()
    for key, values in orders.items():
        line_items_json = []
        for value in values:
            line_items_json.append({
                'order_id': orders_dict[key],
                'key_value_name': "{:.2f}".format(value / 100),
                'key_value_id': values_ids["{:.2f}".format(value / 100)],
                'li_name': name_prefix + "{:06.2f}".format(value / 100)
            })
        line_items_dict[key] = line_items_json
    return line_items_dict

def get_buckets_line_item_json(dfp_client: DfpClient, line_items_dict, sizes, key_id, currency='EUR', multi_targeting=None):
    ad_unit_id = get_root_unit_id(dfp_client)
    li_json = []
    for key, values in line_items_dict.items():
        for value in values:
            if multi_targeting is not None:
                custom_targeting = multi_targeting[value['key_value_name']]
            else:
                custom_targeting = {"xsi_type": "CustomCriteriaSet",
                                    "logicalOperator": "OR",
                                    "children": [
                                        {"xsi_type": "CustomCriteriaSet",
                                         "logicalOperator": "AND",
                                         "children": [
                                             {"xsi_type": "CustomCriteria",
                                              "keyId": key_id,
                                              "valueIds": [value['key_value_id']],
                                              "operator": "IS"}]
                                         }]
                                    }
            cost_per_unit = float(value['key_value_name'])
            li_json.append(get_line_item_json(value['li_name'], False, value['order_id'], sizes, ad_unit_id,
                                              cost_per_unit, custom_targeting, None, currency, None)) # type: ignore
    return li_json


def get_root_unit_id(dfp_client: DfpClient):
    network_service = dfp_client.GetService(
        "NetworkService", version=VERSION_NB
    )
    network = network_service.getCurrentNetwork()
    return network['effectiveRootAdUnitId']


def get_line_item_json(name, is_adx, order_id, size, ad_unit_id, cost_per_unit_eur=0, custom_targeting=None,
                       price_priority=None, currency="EUR", web_property_code=None):
    """
    Args:
        dfp_client:
        name: line item name
        is_adx: either Adx Exchange or Price Priority
        order_id:
        size:
            - {"width": 123, "height": 456}
            - [{"width": 123, "height": 456}, {"width": 234, "height": 567}]
            - [(123,456),(234,567)]
        ad_unit_id:
        years_lifetime:
        cost_per_unit_eur:
        custom_targeting: None or Buckets Key and Values
        price_priority: used in case of Sponsorship Line Items
        currency: Euros, Dollars, Pounds
        web_property_code: In yieldlove is none by default
    Returns:
    """
    if type(size) == dict:
        size = [size]
    if currency not in ["USD", "EUR", "GBP"]:
        raise Exception("Unknown currency {}.".format(currency))
    creative_placeholders = []
    for s in size:
        if type(s) == dict:
            s = (s["width"], s["height"])
        creative_placeholders.append({
            "size": {
                "width": s[0],
                "height": s[1],
                "isAspectRatio": False
            },
            "expectedCreativeCount": 1,
            "creativeSizeType": "PIXEL"
        })
    if is_adx:
        creative_rotation_type = "EVEN"
        line_item_type = "AD_EXCHANGE"
    else:
        creative_rotation_type = "MANUAL"
        line_item_type = "PRICE_PRIORITY"
        web_property_code = None
    line_item = {
        "orderId": order_id,
        "name": name,
        "startDateTimeType": "IMMEDIATELY",
        "unlimitedEndDateTime": True,
        "creativeRotationType": creative_rotation_type,
        "deliveryRateType": "FRONTLOADED",
        "roadblockingType": "ONE_OR_MORE",
        "lineItemType": line_item_type,
        "costPerUnit": {
            "currencyCode": currency,
            "microAmount": int(cost_per_unit_eur * 1000000)
        },
        "costType": "CPM",
        "creativePlaceholders": creative_placeholders,
        "webPropertyCode": web_property_code,
        "targeting": {
            "inventoryTargeting": {
                "targetedAdUnits": [{
                    "adUnitId": ad_unit_id,
                    "includeDescendants": True
                }]
            },
            "technologyTargeting": ""
        },
        "primaryGoal": {
            "goalType": "NONE",
            "unitType": "IMPRESSIONS",
            "units": -1
        }
    }

    if price_priority is not None and type(price_priority) == int:
        line_item["priority"] = price_priority
    if custom_targeting is not None:
        line_item["targeting"]["customTargeting"] = custom_targeting
    return line_item

def create_line_item_bulk(dfp_client: DfpClient, line_items):
    start_index = 0
    limit = 200
    li_items = []
    logging.info(f'create_line_item_bulk: {line_items}')
    while True:
        if start_index + limit < len(line_items):
            li_items.extend(check_create_line_items(
                dfp_client, line_items[start_index: start_index + limit]))
        else:
            li_items.extend(check_create_line_items(
                dfp_client, line_items[start_index: len(line_items)]))
            break
        start_index += limit
    return li_items

def check_create_line_items(dfp_client: DfpClient, line_items, skip_existing=True):
    """
    Creates line items in dfp.
    :param dfp_client: Client for API call
    :param line_items: list of line item objects
    :param skip_existing: when True creation of line items with a name for which there already is a line item
        are skipped
    :return:
    """
    existing_items = []
    if skip_existing:
        existing_items = get_line_items_by_names(dfp_client, [item['name'] for item in line_items])
        existing_item_names = {item['name'] for item in existing_items}
        line_items = [item for item in line_items if item['name'] not in existing_item_names]
    results = []
    if line_items:
        service = dfp_client.GetService('LineItemService', version=VERSION_NB)
        results = service.createLineItems(line_items)
    return results + existing_items

def get_line_items_by_names(dfp_client: DfpClient, names):
    if not names:
        return []
    service = dfp_client.GetService('LineItemService', version=VERSION_NB)
    query = "WHERE name IN ({})".format(', '.join(["'{}'".format(name) for name in names]))
    statement = dfp.FilterStatement(query)
    response = service.getLineItemsByStatement(statement.ToStatement())
    if "results" not in response:
        return []
    return response["results"]

def create_master_creative_and_get_id(dfp_client: DfpClient, creative_name, snippet, advertiser_id, size=(1, 1)):
    creative_id = get_creatives_by_names(dfp_client, [creative_name])
    if len(creative_id) > 0:
        return creative_id[0]['id']
    else:
        creative_size = {"width": size[0], "height": size[1]}
        creative_id = create_third_party_creative(dfp_client, creative_name, creative_size, snippet, advertiser_id)['id']
        return creative_id


def get_creatives_by_names(dfp_client: DfpClient, creative_names):
    creative_service = dfp_client.GetService('CreativeService', version=VERSION_NB)

    keys = ['key' + str(idx) for idx in range(len(creative_names))]
    # check for existing keys
    stmt_values = "WHERE name IN ({})".format(', '.join([':' + key for key in keys]))

    values = []
    for idx, val in enumerate(creative_names):
        values.append(
            {
                "key": keys[idx],
                "value": {
                    "xsi_type": "TextValue",
                    "value": val
                }
            }
        )
    statement_values = dfp.FilterStatement(stmt_values, values)

    return get_all_results_by_statement(creative_service.getCreativesByStatement, statement_values)

def create_third_party_creative(
        dfp_client: DfpClient, name, size, snippet, advertiser_id, safe_frame=False):
    """
    :param dfp_client:
    :param name:
    :param size:  {"width": <int>, "height": <int>}
    :param snippet:
    :param advertiser_id:
    :return:
    """
    creatives = [{
        'xsi_type': 'ThirdPartyCreative',
        'name': name,
        'advertiserId': advertiser_id,
        'size': size,
        'snippet': snippet,
        'lockedOrientation': 'FREE_ORIENTATION',
        'isSafeFrameCompatible': safe_frame
    }]
    creative_service = dfp_client.GetService(
        'CreativeService', version=VERSION_NB
    )
    res = creative_service.createCreatives(creatives)
    return res[0]

def create_licas_buckets(dfp_client: DfpClient, master_creative_id, li_ids, sizes):
    creative_sizes = [{"width": w, "height": h} for (w, h) in sizes]
    licas = [{"creativeId": master_creative_id, "lineItemId": li_id, "sizes": creative_sizes}
             for li_id in li_ids]
    start_index = 0
    while True:
        if start_index + 200 < len(licas):
            check_create_licas(dfp_client, licas[start_index: start_index + 200])
            start_index += 200
        else:
            check_create_licas(dfp_client, licas[start_index: len(licas)])
            break

def check_create_licas(dfp_client: DfpClient, licas, skip_existing=True):
    existing_licas = []
    if skip_existing:
        existing_licas = get_licas(dfp_client, [(item['lineItemId'], item['creativeId']) for item in licas])
        existing_lica_id_tuples = {(item['lineItemId'], item['creativeId']) for item in existing_licas}
        licas = [item for item in licas if (item['lineItemId'], item['creativeId']) not in existing_lica_id_tuples]

    results = []
    if licas:
        srv = dfp_client.GetService('LineItemCreativeAssociationService', version=VERSION_NB)
        results = srv.createLineItemCreativeAssociations(licas)

    return results + existing_licas

def get_licas(dfp_client: DfpClient, lica_id_tuples):
    service = dfp_client.GetService('LineItemCreativeAssociationService', version=VERSION_NB)
    query = 'WHERE ' + ' OR '.join(['(lineItemId={li_id} AND creativeId={cr_id})'.format(li_id=tup[0], cr_id=tup[1])
                                    for tup in lica_id_tuples])
    statement = dfp.FilterStatement(query)

    return get_all_results_by_statement(service.getLineItemCreativeAssociationsByStatement, statement)

def create_buckets_additional_keys(dfp_client: DfpClient, additional_keys):
    keys_dict = {item['key_name']: get_bucket_key(dfp_client, item['key_name'], item['key_type'])
                 for item in additional_keys}
    return keys_dict

# def create_sucbid_values(dfp_client: DfpClient, key_prefix='yieldlove_hb_sucbid'):
#     key_id = get_bucket_key(dfp_client, key_prefix)
#     key_values = ["true", "false"]
#     results = None
#     try:
#         results = create_targeting_key_values(dfp_client, key_id, key_values)
#     except Exception as e:
#         if "CustomTargetingError.VALUE_NAME_DUPLICATE" in str(e.args):
#             results = get_all_key_values(dfp_client, key_name='yieldlove_hb_sucbid', only_active=True, as_dict=False)
#     return results

def create_targeting_key_values(dfp_client: DfpClient, key_id: int, key_name:str, key_values):
    """
    Create the key values for a targeting key with the given id.
    :param dfp_client: (googleads.dfp.DfpClient) Client for API call
    :param key_id: id of the key to be checked
    :param key_values: values which should be created for the targeting key
    """
    cts = dfp_client.GetService("CustomTargetingService", version=VERSION_NB)
    existing_values = get_all_key_values(dfp_client, key_name, only_active=False, as_dict=False)
    values = []
    for name in key_values:
        # only create the values which are not already existing
        if name in [value['name'] for value in existing_values]:
            continue
        values.append(
            {
                "customTargetingKeyId": key_id,
                "displayName": name,
                "name": name,
                "matchType": "EXACT",
                "status": "ACTIVE"
            }
        )
    cts.createCustomTargetingValues(values)
    return get_all_key_values(dfp_client, key_name, only_active=False, as_dict=False)


def get_companies(dfp_client: DfpClient, company_ids: list):
    service = dfp_client.GetService('CompanyService', version=VERSION_NB)
    query = 'WHERE id = {}'.format(', '.join([str(id_) for id_ in company_ids]))
    statement = dfp.FilterStatement(query)
    print("QUERY", query)

    return get_all_results_by_statement(service.getCompaniesByStatement, statement)


def get_root_adunit_id(dfp_client: DfpClient):
    network_service = dfp_client.GetService(
        "NetworkService", version=VERSION_NB
    )
    network = network_service.getCurrentNetwork()
    return network['effectiveRootAdUnitId']


def validate_adunits(dfp_client: DfpClient, ad_unit_ids: list[str]):   
    """
    Validate the ad units
    :param dfp_client:
    :param ad_units:
    :return:
    """
    ad_unit_service = dfp_client.GetService('InventoryService', version=VERSION_NB)
    query = "WHERE id IN ({})".format(', '.join(["'{}'".format(ad_unit) for ad_unit in ad_unit_ids]))
    statement = dfp.FilterStatement(query)
    response = ad_unit_service.getAdUnitsByStatement(statement.ToStatement())
    if "results" not in response:
        logging.error("No ad units found for the given ids.")
        exit(1)
    if len(response["results"]) != len(ad_unit_ids):
        logging.error("Not all ad units were found. Please check the ids.")
        exit(1)
    return response["results"]

def create_creative_set(dfp_client: DfpClient, creative_set_name, master_creative_id, companion_creative_ids): 
    creative_set_json = {
        'name': creative_set_name,
        'masterCreativeId': master_creative_id,
        'companionCreativeIds': companion_creative_ids
    }
    creative_set_service = dfp_client.GetService('CreativeSetService', version=VERSION_NB)
    
    return creative_set_service.createCreativeSet(creative_set_json)


def create_licas_buckets_creative_set(dfp_client: DfpClient, creative_set_id, master_creative_id, li_ids):
    licas = [{"creativeSetId": creative_set_id, 'creativeId': master_creative_id, "lineItemId": li_id}
             for li_id in li_ids]
    start_index = 0
    while True:
        if start_index + 200 < len(licas):
            check_create_licas_creative_set(dfp_client, licas[start_index: start_index + 200])
            start_index += 200
        else:
            check_create_licas_creative_set(dfp_client, licas[start_index: len(licas)])
            break

def check_create_licas_creative_set(dfp_client: DfpClient, licas, skip_existing=True):
    existing_licas = []
    if skip_existing:
        existing_licas = get_licas_creative_set(dfp_client, [(item['lineItemId'], item['creativeSetId'], item['creativeId']) for item in licas])
        existing_lica_id_tuples = {(item['lineItemId'], item['creativeId']) for item in existing_licas}
        licas = [item for item in licas if (item['lineItemId'], item['creativeId']) not in existing_lica_id_tuples]

    licas = [{'lineItemId': item['lineItemId'], 'creativeSetId': item['creativeSetId']} for item in licas]
    results = []
    if licas:
        srv = dfp_client.GetService('LineItemCreativeAssociationService', version=VERSION_NB)
        results = srv.createLineItemCreativeAssociations(licas)
    return results + existing_licas

def get_licas_creative_set(dfp_client: DfpClient, lica_id_tuples):
    service = dfp_client.GetService('LineItemCreativeAssociationService', version=VERSION_NB)
    query = 'WHERE ' + ' OR '.join(['(lineItemId={li_id} AND creativeId={cr_id})'.format(li_id=tup[0], cs_id=tup[1], cr_id=tup[2])
                                    for tup in lica_id_tuples])
    statement = dfp.FilterStatement(query)
    return get_all_results_by_statement(service.getLineItemCreativeAssociationsByStatement, statement)

