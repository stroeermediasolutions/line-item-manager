1. `source venv/bin/activate`
2. `pip install -r requirements.txt`
3. Create a API Key for google admanager api here: https://console.cloud.google.com/apis/dashboard (see doc: https://developers.google.com/ad-manager/api/authentication)
4. Create a folder `secret` at the top level of the directory and paste your api-key-file from step 3 into the folder 
5. create a googleads.yaml on the top level of the directory and paste the following syntax in it:
    ```yaml
    ad_manager:
        application_name: prebid-line-item-creator
        network_code: YOUR_GOOGLE_ADMANAGER_NETWORK_CODE
        path_to_private_key_file: PATH_TO_YOUR_SECRET_FILE
    ```

6. Then you should be able to run a console command following this pattern:
    ```
    python line-item-creator.py --format wallpaper --dfp-id <your-dfp-id> --line-item-type sponsorship --line-item-priority 4 --master-size 728x90 --companion-size 160x600 --start-price-bucket 500 --end-price-bucket 550 --price-bucket-step 25 --advertiser-id <your-advertiser-id> --trafficker-id <your-trafficker-id>
    ```
    company_id can be read from url in gam in admin/companies/whatevercompanyyouwant
   
    your_account_id can be read from url in gam in admin/accessauthorization/youruseraccount
   
    IMPORTANT:
   
    Only add --write true if you want to actually create all orders, line-items and creatives in the google admanager
    As long as --write false (or not defined) this script will only demonstrate the creation and prints the output into the terminal
