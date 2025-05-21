import datetime
from enum import Enum
import logging
from typing import Union

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


# allowed formats (can be expanded)
class Formats(Enum):
    WALLPAPER = 'wallpaper'
    FIREPLACE = 'fireplace'

    def __str__(self):
        return self.value

# allowed line item types (can be expanded)
class LineItemTypes(Enum):
    STANDARD = 'standard'
    SPONSORSHIP = 'sponsorship'
    NETWORK = 'network'
    BULK = 'bulk'
    PRICE_PRIORITY = 'price-priority'
    HOUSE = 'house'

    def __str__(self):
        return self.value

def validate_format_name(format_name: str) -> str:
    cleaned_format_name = format_name.lower()
    if cleaned_format_name not in [format.value for format in Formats]:
        logging.error(f"Invalid format name: {format_name}. Allowed values are: {[format.value for format in Formats]}.")
        raise ValueError
    return cleaned_format_name

def validate_line_item_type(line_item_type: str) -> str:
    cleaned_line_item_type = line_item_type.lower()
    if cleaned_line_item_type not in [item.value for item in LineItemTypes]:
        logging.error(f"Invalid line item type: {line_item_type}. Allowed values are: {[item.value for item in LineItemTypes]}.")
        raise ValueError
    return cleaned_line_item_type.replace('-', '_') # convert to underscores for gam compatibility

def validate_line_item_priority(priority) -> int:
    try:
        priority = int(priority)
    except (ValueError, TypeError):
        logging.error(f"Given priority is not an integer: {priority}.")
        raise TypeError
    
    if priority < 0 or priority > 14:
        logging.error(f"Invalid line item priority: {priority}. Allowed values are between 0 and 14.")
        raise ValueError
    return int(priority)

def validate_single_size(size: str) -> list[int]:
    """Validate the creative size format.
    The expected format is 'widthxheight', where width and height are integers.
    The width and height must be greater than 0 and less than or equal to 2000.

    Args:
        size (str): The creative size string to validate.

    Returns:
        list[int]: The validated creative size.
    """

    if not size:
        logging.error("Creative size cannot be empty.")
        raise ValueError
    if size.count('x') != 1:
        logging.error(f"Invalid creative size format: {size}. Expected format is 'widthxheight'.")
        raise ValueError
    width, height = size.split('x')
    try:
        width = int(width)
        height = int(height)
    except ValueError:
        logging.error(f"Invalid creative size dimensions: {size}. Width ({width}) and height ({height}) must be integers.")
        raise ValueError
    if width <= 0 or height <= 0:
        logging.error(f"Invalid creative size dimensions: {size}. Width ({width}) and height ({height}) must be greater than 0.")
        raise ValueError
    if width > 2000 or height > 2000:
        logging.error(f"Invalid creative size dimensions: {size}. Width ({width}) and height ({height}) must be less than or equal to 2000.")
        raise ValueError
    return [width, height]

def validate_multiple_sizes(sizes: str) -> list[list[int]]:
    """Validate the companion sizes format.
    The expected format for a single size is 'widthxheight', where width and height are integers.
    The width and height must be greater than 0 and less than or equal to 2000.

    Args:
       sizes (str): The size strings to validate, comma separated.
    Returns:
        list[list[int]]: A list of validated companion sizes.
    """
    if not sizes:
        logging.error("Companion size cannot be empty.")
        raise ValueError
    size_list = [size.strip() for size in sizes.split(',')]
    sizes_as_ints = []
    for size in size_list:
        sizes_as_ints.append(validate_single_size(size))
    return sizes_as_ints

def validate_advertiser_id(advertiser_id) -> int:
    try:
        advertiser_id = int(advertiser_id)
    except (ValueError, TypeError):
        logging.error(f"Advertiser ID must be an integer, got {advertiser_id}")
        raise TypeError
    if advertiser_id <= 0:
        logging.error(f"Invalid advertiser ID: {advertiser_id}. Allowed values are greater than 0.")
        raise ValueError
    return advertiser_id

def validate_trafficker_id(trafficker_id) -> int:
    try:
        trafficker_id = int(trafficker_id)
    except (ValueError, TypeError):
        logging.error(f"Trafficker ID must be an integer, got {trafficker_id}")
        raise TypeError
    if trafficker_id <= 0:
        logging.error(f"Invalid trafficker ID: {trafficker_id}. Allowed values are greater than 0.")
        raise ValueError
    return trafficker_id

def validate_dfp_id(dfp_id) -> int:
    try:
        dfp_id = int(dfp_id)
    except Exception:
        logging.error(f"DFP ID must be an integer, got {dfp_id}")
        raise TypeError
    if dfp_id <= 0:
        logging.error(f"Invalid DFP ID: {dfp_id}. Allowed values are greater than 0.")
        raise ValueError
    return dfp_id
          
def validate_start_date(start_date: str) -> str:
    return validate_date_format(start_date, '--start-time')
    
def validate_end_date(end_date: str) -> str:
    return validate_date_format(end_date, '--end-time')

def validate_date_format(date_str: str, attr: str) -> str:
    """Validate the date format.
    The expected format is 'YYYY-MM-DD HH:MM:SS'.

    Args:
        date_str (str): The date string to validate.
        attr (str): The input's name for validation.

    Returns:
        datetime: the validated datetime object or
        str: the original string if it is 'immediately' or 'unlimited'.
    """

    date_str = date_str.lower().strip()

    if date_str and date_str != 'immediately' and date_str != 'unlimited' and date_str != 'one_hour_from_now':
        # Check if the date string matches the expected format
        try:
            time_as_datetime = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            # Check if the date is in the future
            if time_as_datetime < datetime.datetime.now():
                logging.error(f"Invalid date: {date_str}. Date must be in the future.")
                raise ValueError
            return date_str
        except ValueError:
            if attr == '--start-time':
                logging.error(f"Invalid start time: {date_str}. Allowed values are 'YYYY-MM-DD HH:MM:SS' or 'one_hour_from_now' or 'immediately'.")
                raise ValueError
            elif attr == '--end-time':
                logging.error(f"Invalid end time: {date_str}. Allowed values are 'unlimited' or 'YYYY-MM-DD HH:MM:SS'.")
                raise ValueError
    
    elif (date_str == 'immediately' or date_str == 'one_hour_from_now') and attr == '--start-time':
        return date_str
    
    elif date_str == 'unlimited' and attr == '--end-time':
        return date_str
    
    # If the date string is not 'immediately' or 'unlimited', raise an error - not sure we ever get here tbh
    logging.error(f"Invalid date format: {date_str}. Expected format is 'YYYY-MM-DD HH:MM:SS' or 'immediately'/'one_hour_from_now'/'unlimited'.")
    raise ValueError

def validate_start_and_end_time(start_time: str, end_time:str):
    if start_time.lower() != 'immediately' and start_time.lower() != 'one_hour_from_now' and end_time.lower() != 'unlimited' and datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S') > datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S'):
        logging.error(f"Invalid time range: start time: {start_time} must be before end time: {end_time}.")
        raise ValueError

def validate_target_ad_units(target_ad_units: str) -> list[str]:
    """Validate the target ad units format.
    The expected format is a comma-separated list of ad units.

    Args:
        target_ad_units (str): The target ad units string to validate.

    Returns:
        list[str]: A list of validated target ad units.
    """
    if not target_ad_units:
        return []
    
    ad_unit_list = [ad_unit.strip() for ad_unit in target_ad_units.split(',')]
        
    # Check for duplicates
    if len(ad_unit_list) != len(set(ad_unit_list)):
        logging.error(f"Duplicate target ad units found: {target_ad_units}. Target ad units must be unique.")
        raise ValueError
    
    return ad_unit_list

def validate_price_bucket(start_price: float, end_price: float, step: float):
    if start_price < 0:
        logging.error(f"Invalid start price bucket ({start_price}). Allowed values are greater than or equal to 0.")
        raise ValueError
    if end_price < 0:
        logging.error(f"Invalid end price bucket ({end_price}). Allowed values are greater than or equal to 0.")
        raise ValueError
    if step < 0:
        logging.error(f"Invalid price bucket step ({step}). Allowed values are greater than or equal to 0.")
        raise ValueError
    # Check if start price is less than end price
    if start_price > end_price:
        logging.error(f"Invalid price bucket range: start price ({start_price}) must be less than end price ({end_price}).")
        raise ValueError
    if step > (end_price - start_price):
        logging.error(f"Invalid price bucket step ({step}). It must be less than the difference between end price: {end_price} and start price ({start_price}). (currently: {end_price - start_price}).")
        raise ValueError
    # Check if step is a exact partial of the difference between start and end price
    if (end_price - start_price) % step != 0:
        logging.warning(f"Problematic price bucket step: {step}. It should be a partial of the difference between end price ({end_price}) and  ({start_price}) (currently: {end_price - start_price}).")

def validate_format(format: str, creatives_size: str, companion_sizes: list[str]): 
    logging.info(f"Validating format: {format} with creatives size: {creatives_size} and companion sizes: {companion_sizes}")
    if format == Formats.WALLPAPER.value:
        if len(companion_sizes) != 1:
            logging.error(f"Wallpaper needs a master-size and exactly 1 companion-size. You gave {len(companion_sizes)} companion sizes: {companion_sizes}")
            raise ValueError
    if format == Formats.FIREPLACE.value:
        if len(companion_sizes) != 2:
            logging.error(f"Fireplace needs a master-size and exactly 2 companion-size. You gave {len(companion_sizes)} companion sizes: {companion_sizes}")
            raise ValueError
