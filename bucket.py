import datetime
import logging
from textwrap import dedent

import pytz
import dfp_api
from validation_helper import Formats, LineItemTypes

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class Buckets():
    
    format: str = ''
    line_item_type: str = ''
    line_item_priority: int = 14
    creative_size: list[int] = [] # [width, height]
    companion_sizes: list[list[int]] = [] # [[width, height], [width, height]]
    start_time: str = '' # defaults to immediately
    end_time: str = '' # defaults to unlimited
    price_bucket_key_value_name: str = '' # this is the key-value-name for price buckets from the customer (defaults to stroeer_ssp_hb_pb)
    hb_adid_parameter: str = '' # this it the parameter for the universal-creative's adid (defaults to hb_adid)
    start_price_bucket: int = 0
    end_price_bucket: int = 0
    price_bucket_step: int = 0 
    # price_bucket_amount: int = 0 # maybe add as optional later (three of the four price bucket options to calculate the other?)
    advertiser_id: int = 0
    trafficker_id: int = 0
    dfp_id: int = 0
    write: bool = False # don't think we need this here
    currency: str = '' # defaults to EUR - is that something we actually need? adservers have a default don't they?
    prefix: str = 'stroeer_ssp'
    target_ad_units: list[str] = [] # defaults to empty

    def __init__(self, args):
        
        self.format = args['format'] # format name (e.g. wallpaper, fireplace)
        self.line_item_type = args['line_item_type'] # line item type, set line item priority seperately via --line_item_priority
        self.line_item_priority = args['line_item_priority'] # line item priority (0-14)
        self.creative_size = args['master_size'] # creative size (e.g. 728x90)
        self.companion_sizes = args['companion_sizes'] # companion sizes (e.g. 120x600, 200x600)
        self.start_time = args['start_time'] # defaults to immediately
        self.end_time = args['end_time'] # defaults to unlimited
        self.price_bucket_key_value_name = args['price_bucket_key_value_name'] 
        self.hb_adid_parameter = args['hb_adid_parameter']
        self.start_price_bucket = args['start_price_bucket']
        self.end_price_bucket = args['end_price_bucket']
        self.price_bucket_step = args['price_bucket_step']
        # self.price_bucket_amount: int = 0 # maybe add as optional later (three of the four price bucket options to calculate the other?)
        self.advertiser_id = args['advertiser_id'] 
        self.trafficker_id = args['trafficker_id'] 
        self.dfp_id = args['dfp_id'] 
        self.write = args['write'] # write to dfp
        self.currency = args['currency']
        self.target_ad_units = args['target_ad_units'] # defaults to empty
        
        self.name_prefix = f"{self.prefix}_pb" 
        self.format_key_name = f"{self.prefix}_format" 
        self.master_creative_name = f"{self.prefix}_{self.format}_hb_master_creative" 
        self.companion_creative_name = f"{self.prefix}_{self.format}_hb_companion_creative" 

        # customize to be price-bucket and format name ? Not sure that's here already
        self.additional_keys = [{'key_name': self.format_key_name, "key_type": 'PREDEFINED'}] 
        
        self.format_key_values = [format.value for format in Formats]

        # prebid universal creative with custom pattern-names
        self.master_snippet = dedent(
            f"""
                <script src = "https://cdn.jsdelivr.net/npm/prebid-universal-creative@latest/dist/%%PATTERN:hb_format%%.js"></script>
                <script>
                    var ucTagData = {{}};
                    ucTagData.adServerDomain = "";
                    ucTagData.pubUrl = "%%PATTERN:url%%";
                    ucTagData.targetingMap = %%PATTERN:TARGETINGMAP%%;
                    ucTagData.hbPb = "%%PATTERN:{self.price_bucket_key_value_name}%%";
                    ucTagData.hbFormat = "%%PATTERN:hb_format%%";
                    ucTagData.adId = "%%PATTERN:{self.hb_adid_parameter}%%";
                    // if you're using GAM and want to track outbound clicks on native ads you can add this line
                    ucTagData.clickUrlUnesc = "%%CLICK_URL_UNESC%%";
                    ucTagData.requestAllAssets = true;

                    try {{
                        ucTag.renderAd(document, ucTagData);
                    }} catch (e) {{
                        console.log(e);
                    }}
                </script>
            """
        )

        # create creative template for companion; create creatives 1 companion for wallpaper and 2 new companions for fireplace
        self.companion_snippet = dedent(
            """
                <script></script>
            """
        )
                        

    def create_line_item_price_buckets(self, start_price_bucket: int, end_price_bucket: int, price_bucket_step: int) -> list[int]:
        """
        Creates the line item price buckets.
        Args:
            start_price_bucket (int): The start price bucket.
            end_price_bucket (int): The end price bucket.
            price_bucket_step (int): The price bucket step.
        Returns:
            list: A list of price buckets.
        """
        price_buckets = []

        price_bucket_amount:float = (end_price_bucket - start_price_bucket ) / price_bucket_step + 1
        logging.info(f'Calculated price_bucket amount is: {price_bucket_amount}')

        if price_bucket_amount.is_integer():
            for x in range(0, int(price_bucket_amount)):
                price_buckets.append(start_price_bucket + (x * price_bucket_step))
        else: 
            logging.warning(f'Price_bucket amount is not an integer, therefore end_price_bucket will be set in disregard of the step_size')
            for x in range(0, price_bucket_amount.__floor__()):
                price_buckets.append(start_price_bucket + (x * price_bucket_step))
            price_buckets.append(end_price_bucket)

        return price_buckets


    def create_price_buckets_per_order(self, price_buckets: list) -> list:

        max_price_buckets_per_order = 400
        
        order_amount = (price_buckets.__len__() / max_price_buckets_per_order).__ceil__()

        logging.info(f'{price_buckets.__len__()} price_buckets will be created in : {order_amount} orders')

        orders_with_price_buckets = [price_buckets[i:i + max_price_buckets_per_order] for i in range(0, len(price_buckets), max_price_buckets_per_order)]

        return orders_with_price_buckets

        
    def assemble_orders(self, orders_with_price_buckets: list[list[int]]) -> dict[str, list[int]]:
        """
        Assembles the orders with the price buckets.

        Args:
            orders_with_price_buckets (List): A list of orders with price buckets.

        Returns:
            Dict: A dictionary of orders with price buckets.
        """

        orders = {}
        for i, order in enumerate(orders_with_price_buckets):
            # stroeer_ssp_wallpaper_5.0-10.0
            order_name = f'{self.prefix}_{self.format}_{order[0]/100}-{order[-1]/100}'
            orders[order_name] = order
        return orders



    def assemble_line_item_jsons(self, orders: dict[str, list[int]], pb_key_id: int, pb_value_ids: list[dict], format_key_id: int, format_value_ids: list[dict], orders_dict: dict = {}) -> list[dict]:
        li_jsons = []
        
        endDateObj = self.define_end_date()
        
        startDateTimeType = None
        if self.start_time == 'immediately':
            startDateTimeType = 'IMMEDIATELY'
        elif self.start_time == 'one_hour_from_now':
            startDateTimeType = 'ONE_HOUR_FROM_NOW'
        else:
            startDateTimeType = 'USE_START_DATE_TIME'
        
        creativePlaceholder = [
            { # use assemble_size_dict here
                'size': {'width': self.creative_size[0], 'height': self.creative_size[1]},
                'companions': [
                    {
                        'size': {'width': self.companion_sizes[i][0], 'height': self.companion_sizes[i][1]},
                        # 'companionDeliveryOption': 'USE_COMPANION_DELIVERY_OPTION'
                    } for i in range(len(self.companion_sizes))
                ]
            }
        ]
               
        format_value_id = next((item for item in format_value_ids if item["name"] == self.format), dict())
        
        primaryGoal = self.create_goal_type_object()
        
        # TODO: Use Order-dict for order-id instead of requesting IDs again
        for order, values in orders.items():
            # print(f'single order: {order}')
            orderId = orders_dict[order] if orders_dict.__len__() > 0 else 0
            # orderId = dfp_api.get_orders_by_names(self.dfp_client, [order])[0]['id']
            logging.info(f'orderId: {orderId}')
            for lineitem in values:
                # print(f'line item pb {lineitem}')
                
                costPerUnit = {
                    'currencyCode': self.currency,
                    'microAmount': lineitem * 10000 # lineitems are in cents, so multiply by 10000 to get to microAmount
                }

                pb_value_id = next((item for item in pb_value_ids if round(float(item["name"])*100) == lineitem), dict())

                targeting = {
                    'inventoryTargeting': {
                        'targetedAdUnits': [{'adUnitId': adunitId} for adunitId in self.target_ad_units]
                    }, 
                    "customTargeting": {
                        'logicalOperator': 'AND',
                        'children': [
                            {
                                'xsi_type': 'CustomCriteria',
                                'keyId': pb_key_id,
                                'valueIds': [pb_value_id['id']],
                                'operator': 'IS'
                            },
                            {
                                'xsi_type': 'CustomCriteria',
                                'keyId': format_key_id,
                                'valueIds': [format_value_id['id']],
                                'operator': 'IS'
                            }
                        ]
                    }
                } 
                                                            
                li_json = {
                    'orderId': orderId, 
                    'name': f'{self.prefix}_{self.format}_{lineitem/100}', 
                    'startDateTime': self.start_time,
                    'startDateTimeType': startDateTimeType,
                    'endDateTime': endDateObj['endDateTime'],
                    'unlimitedEndDateTime': endDateObj['unlimitedEndDateTime'],
                    'creativeRotationType': 'EVEN',
                    'companionDeliveryOption': 'ALL',
                    'roadblockingType': 'CREATIVE_SET',
                    'lineItemType': self.line_item_type.upper(),
                    'priority': self.line_item_priority,
                    'costPerUnit': costPerUnit,
                    'costType': 'CPM',
                    'creativePlaceholders': creativePlaceholder,
                    'targeting': targeting,
                    'primaryGoal': primaryGoal
                }
                li_jsons.append(li_json)
            
        return li_jsons
                
                
    

    # create stroeer_ssp_hb_pb key-values if no publisher key-value is given
    def create_price_bucket_key_values(self, line_item_price_buckets, key_id):
        logging.info(f'Creating price bucket key-values for {self.price_bucket_key_value_name}')
        # this should create the ssp price bucket, automatically skips existing yay
        key_values = dfp_api.create_hb_key_values(self.dfp_client, line_item_price_buckets, key_id, self.price_bucket_key_value_name, return_all=False)
        return key_values

    # map calculated price buckets to publisher's price-bucket key-values
    def map_line_items_to_existing_price_buckets(self, line_item_price_buckets: list[int], price_bucket_key):
        existing_pricebucket_obj = dfp_api.get_all_key_values(self.dfp_client, self.price_bucket_key_value_name)
        # get name, cast to int and then to cent units (need to round because of float inaccuracy)
        existing_pricebucket: list[int] = [round(float(x['name'])*100) for x in existing_pricebucket_obj]
        existing_pricebucket.sort()
        
        # just a flag to create helpful logging
        mapping_necessary = False
        
        used_price_buckets: list[int] = []
        
        # add matching price-buckets and use next-higher value
        for pb in line_item_price_buckets:
            if pb not in existing_pricebucket:
                for expb in existing_pricebucket:
                    if pb < expb:
                        used_price_buckets.append(expb)
                        mapping_necessary = True
                        break                
            else: 
                used_price_buckets.append(pb)
        
        if mapping_necessary:
            logging.info(f'Desired price-buckets will be mapped to: {used_price_buckets}')
        else:
            logging.info(f'No mapping necessary, using desired price-buckets: {used_price_buckets}')

        return used_price_buckets
    
    
    def create_goal_type_object(self):
        if self.line_item_type in [LineItemTypes.STANDARD.value, LineItemTypes.BULK.value]:
            return {
                'goalType': 'LIFETIME',
                'unitType': 'IMPRESSIONS',
                'units': 100000 # absolute impressions (honestly no clue how to define this without publisher input)
            }
        elif self.line_item_type in [LineItemTypes.SPONSORSHIP.value, LineItemTypes.NETWORK.value, LineItemTypes.HOUSE.value]:
            return {
                'goalType': 'DAILY',
                'unitType': 'IMPRESSIONS',
                'units': 100 # percentage
            }
        else: # PRICE_PRIORITY 
            # NONE
            return {
                'goalType': 'NONE'
            }
    
    def define_end_date(self): 
        if self.end_time == 'unlimited' and self.line_item_type in [LineItemTypes.SPONSORSHIP.value, LineItemTypes.NETWORK.value, LineItemTypes.PRICE_PRIORITY.value, LineItemTypes.HOUSE.value]:
            return {
                'endDateTime': 'unlimited',
                'unlimitedEndDateTime': True
            }
        elif self.end_time == 'unlimited':
            # if unlimited is not allowed, just add 10 years from now 
            logging.warning(f'selected line-item-type ({self.line_item_type}) does not allow "unlimited" as end-time; mapping to ten years from now')
            return {
                'endDateTime': (datetime.datetime.now(pytz.utc) + datetime.timedelta(days=(365*10))).replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S'),
                'unlimitedEndDateTime': False
            }
        return {
            'endDateTime': datetime.datetime.strptime(self.end_time, "%Y-%m-%d %H:%M:%S").replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S'),
            'unlimitedEndDateTime': False
        }
        
    def assemble_size_list(self, size: list[int]) -> list[int]: 
        return [size[0], size[1]]
        
    def create_creative_set(self) -> dict: 
        # use creativesetservice to create creatives set out of master-creative and companion-creative https://developers.google.com/ad-manager/api/reference/v202502/CreativeSetService.CreativeSet
                
        # create master creative if not already created (function automatically does this check)
        master_master_creative_id = dfp_api.create_master_creative_and_get_id(self.dfp_client, self.master_creative_name, self.master_snippet, self.advertiser_id, self.assemble_size_list(self.creative_size))
        
        logging.info(f'master master-creative created with id: {master_master_creative_id}')
        
        logging.info(f'companion sizes: {self.companion_sizes}')
        
        # create companion creative if not already created
        # need to think this through... only needs to be blocker ?
        companion_master_creative_ids = [dfp_api.create_master_creative_and_get_id(self.dfp_client, f'{self.companion_creative_name}_{index}', self.companion_snippet, self.advertiser_id, self.assemble_size_list(companion_size)) for index, companion_size in enumerate(self.companion_sizes)]
        
        logging.info(f'companion master-creative created with id: {companion_master_creative_ids}')

        creative_set_name = f'{self.prefix}_{self.format}_creative_set'

        creative_set = dfp_api.create_creative_set(self.dfp_client, creative_set_name, master_master_creative_id, companion_master_creative_ids)
        return {
            'creativeSetId': creative_set['id'],
            'masterCreativeId': master_master_creative_id,
            'companionCreativeIds': companion_master_creative_ids
        }
    
# ----------- dry run to test parameters, will make calls to dfp but only getters, no writing done here -----------    
    
    def dry_run(self):
        
        # check that network name is valid
        self.dfp_client = dfp_api.get_dfp_client_for_account('googleads.yaml')
        print(f'dfp_client from admanager: {self.dfp_client.network_code}')
        
        line_item_price_buckets = self.create_line_item_price_buckets(self.start_price_bucket, self.end_price_bucket, self.price_bucket_step)
        
        # just info on price-bucket usage & line-item-mapping if necessary
        if self.price_bucket_key_value_name == 'stroeer_ssp_hb_pb':
           logging.info('No custom key-value for price-buckets set, will create new key-value "stroeer_ssp_hb_pb"')
        else:
            # check here if passed key-value for price bucket exists and print error if not, we only want to create ssp
            key_id = dfp_api.check_bucket_key(self.dfp_client, self.price_bucket_key_value_name)
            self.map_line_items_to_existing_price_buckets(line_item_price_buckets, key_id)

        # use potentially mapped price-buckets to create orders        
        orders_with_buckets_list = self.create_price_buckets_per_order(line_item_price_buckets)
        orders = self.assemble_orders(orders_with_buckets_list) 

        print(f'Orders with buckets: {orders}')

        # check that given ad_units are valid
        if not self.target_ad_units:
            # try to get root_adunit_id (hopefully this represents run of network, but I don't know)
            self.target_ad_units = [dfp_api.get_root_adunit_id(self.dfp_client)]
        else:
            # validate target adunits; exits if invalid adunit is passed
            dfp_api.validate_adunits(self.dfp_client, self.target_ad_units)

        print(f'Adunits to be targetted: {self.target_ad_units}')

        pb_key_id = 0
        pb_values = [{'name': f'{float(pb)/100}', 'id': 0} for pb in line_item_price_buckets]
        format_key_id = 0
        format_values = [{'name': format, 'id': 0} for format in self.format_key_values]

        # assemble line-item json with a fake order
        li_json = self.assemble_line_item_jsons(orders, pb_key_id, pb_values, format_key_id, format_values, orders_dict={}) 
        
        logging.info(f'expected line items with pb-, format- and order-ids as 0: {li_json}')

# ----------- as the name says, actual run, will create order, line-items & potentially price-buckets in dfp -----------

    def actual_run(self):
        
        self.dfp_client = dfp_api.get_dfp_client_for_account('googleads.yaml')
        print(f'dfp_client from admanager: {self.dfp_client}')

        line_item_price_buckets = self.create_line_item_price_buckets(self.start_price_bucket, self.end_price_bucket, self.price_bucket_step)
        pb_key_id = None
        
        # check if given key for price-buckets exist, if so, use it, else check if key defaulted to stroeer_ssp_hb_pb, then create, else error
        if self.price_bucket_key_value_name == 'stroeer_ssp_hb_pb':
            logging.info('No custom key-value for price-buckets set, will create new key-value "stroeer_ssp_hb_pb"')
            # create key for ssp price bucket
            pb_key_id = dfp_api.get_bucket_key(self.dfp_client, self.price_bucket_key_value_name, 'PREDEFINED')
            # create the price bucket key-values if no publisher key-value is given
            self.create_price_bucket_key_values(line_item_price_buckets, pb_key_id) # don't write result into line_item_price_buckets
        else:
            # try to find given key, throws error and exits if key not found
            pb_key_id = dfp_api.check_bucket_key(self.dfp_client, self.price_bucket_key_value_name)
            # map calculated price buckets to publisher's price-bucket key-values
            line_item_price_buckets = self.map_line_items_to_existing_price_buckets(line_item_price_buckets, pb_key_id)

        # use potentially mapped price-buckets to create orders
        orders_with_buckets_list = self.create_price_buckets_per_order(line_item_price_buckets)
        orders = self.assemble_orders(orders_with_buckets_list) 

        if not self.target_ad_units:
            # set root-adunit as target adunit if no target adunit is given
            # TODO: find out if this is actually run of network (after fixing it oops) & if it's necesary in the first place
            self.target_ad_units = [dfp_api.get_root_adunit_id(self.dfp_client)]
        else:
            # validate target adunits; exits if invalid adunit is passed
            dfp_api.validate_adunits(self.dfp_client, self.target_ad_units)

        print(f'Adunits to be targetted: {self.target_ad_units}')

        # this should be the order-obj that actually comes back from gam?
        orders_dict = dfp_api.create_orders_buckets(self.dfp_client, list(orders.keys()), str(self.trafficker_id), str(self.advertiser_id))
        print(f'Orders dict: {orders_dict}')

        pb_values = dfp_api.create_hb_key_values(self.dfp_client, line_item_price_buckets, pb_key_id, self.price_bucket_key_value_name, return_all=False)
        format_key_id = dfp_api.get_bucket_key(self.dfp_client, self.format_key_name, 'PREDEFINED') # create format key
        format_values = dfp_api.create_targeting_key_values(self.dfp_client, format_key_id, self.format_key_name, self.format_key_values) # add format values to format key
        
        # assemble line-item json
        li_json = self.assemble_line_item_jsons(orders, pb_key_id, pb_values, format_key_id, format_values, orders_dict) 
        
        # create line items in gam - I don't understand what type the line-item parameter should be
        line_items = dfp_api.create_line_item_bulk(self.dfp_client, li_json) 

        # save ids of the line items
        li_ids = [li['id'] for li in line_items]
        
        logging.info(f'Line item ids after creation: {li_ids}')
        
        creative_dict = self.create_creative_set()
        
        logging.info(f'creative_dict: {creative_dict}')
        
        dfp_api.create_licas_buckets_creative_set(self.dfp_client, creative_dict['creativeSetId'], creative_dict['masterCreativeId'], li_ids) 
        
        logging.info('WE RAN THROUGH THE WHOLE CODE WITHOUT ERRORS!!!')
