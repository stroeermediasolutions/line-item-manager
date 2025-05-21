from attr import validate
from validation_helper import *
from argparse import ArgumentParser
from bucket import Buckets

def main():

    args = vars(parse_cli_args())
    print(args)

    # validate combined args
    validate_start_and_end_time(args['start_time'], args['end_time'])
    validate_price_bucket(args['start_price_bucket'], args['end_price_bucket'], args['price_bucket_step'])
    validate_format(args['format'], args['master_size'], args['companion_sizes'])

    print("adunits after validation: ", args['target_ad_units'])

    # call Adserver API to create line items
    bucket = Buckets(args) 
    if args['write']:
        bucket.actual_run()
    else:
        bucket.dry_run()


def parse_cli_args():

    parser = ArgumentParser(
        prog='Prebid Line Item Creator',
        description='This tool allows publishers to create master-companion line-items with different price-buckets inside a Google AdManager automatically, to allow websites to display ads via prebid consisting of multiple adslots - Complex Formats.',
        epilog='Link to the documentation as soon as it is available.'
    )
    parser.add_argument('--dfp-id', required=True, type=validate_dfp_id, 
                        help='GAM Network Code / DFP ID')

    parser.add_argument('--format', type=validate_format_name, required=True, 
                        help='Format name (e.g. wallpaper, fireplace)')

    # TODO: default to price-priority ?
    parser.add_argument('--line-item-type', type=validate_line_item_type, required=True, 
                        help='Line item type, set line item priority seperately via --line-item-priority') 

    parser.add_argument('--line-item-priority', required=True, type=validate_line_item_priority, 
                        help='Line item priority (0-14)') 

    parser.add_argument('--master-size', required=True, type=validate_single_size, 
                        help='Creative size (e.g. 728x90)')

    parser.add_argument('--companion-sizes', required=True, type=validate_multiple_sizes, 
                        help='Companion sizes (e.g. 120x600 or for multiple sizes comma-separated: "120x600, 200x600")')

    parser.add_argument('--start-price-bucket', required=True, type=int, 
                        help='Start price bucket in cents (e.g. 500 for 5.00€)')

    parser.add_argument('--end-price-bucket', required=True, type=int, 
                        help='End price bucket in cents (e.g. 1000 for 10.00€)')

    parser.add_argument('--price-bucket-step', required=True, type=int,
                        help='Price bucket step in cents (e.g. 25 for 0.25€)')

    parser.add_argument('--advertiser-id', required=True, type=validate_advertiser_id, 
                        help='Advertiser ID')

    parser.add_argument('--trafficker-id', required=True, type=validate_trafficker_id, 
                        help='Trafficker ID') 
    
    parser.add_argument('--price-bucket-key-value-name', type=str, default="stroeer_ssp_hb_pb",
                        help='Name of price-bucket key-value, if you want to use an existing price-bucket, add here, otherwise, new stroeer_ssp - price-bucket key-value will be created') 
    
    parser.add_argument('--hb-adid-parameter', type=str, default='hb_adid',
                        help='Name of hb_adid parameter for master-creative. Defaults to hb_adid')
    
    parser.add_argument('--target-ad-units', type=validate_target_ad_units,
                        help='Target ad units, give as comma-separated string, e.g. "adunit1, adunit2", if not specified, all ad units will be targeted')

    parser.add_argument('--currency', type=str, choices=['EUR', 'GDP', 'USD'], default='EUR', 
                        help='Currency for price buckets')
   
    parser.add_argument('--start-time', type=validate_start_date, default='immediately', 
                        help='Start time (YYYY-MM-DD HH:MM:SS)')

    parser.add_argument('--end-time', type=validate_end_date, default='unlimited', 
                        help='End time (YYYY-MM-DD HH:MM:SS)')

    parser.add_argument('--write', type=bool, default=False,
                        help='write to google admanager | only use when you are sure everything is configured correctly') # if true performs creation inside gam

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    main()
