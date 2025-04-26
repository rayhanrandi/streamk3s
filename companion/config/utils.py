import os

from functools import lru_cache

from dotenv import load_dotenv, find_dotenv


@lru_cache
def setup_env() -> None:
    app_env = os.getenv("APP_ENV", "development")  # Default to 'development' if APP_ENV is not set
    
    if app_env == "development":
        print("Environment: Development")
        
        # Find and load the .env file
        env_file = find_dotenv(
            filename=".env",
            raise_error_if_not_found=True,  # Ensure .env is mandatory in development
            usecwd=True
        )
        load_dotenv(env_file, verbose=True)
        print(f"Loaded environment variables from {env_file}")
    elif app_env == "production":
        print("Environment: Production")
    else:
        raise Exception(f"Invalid APP_ENV value: {app_env}. Must be 'development' or 'production'.")
        
def get_env_value(env_variable: str) -> str | int | bool | None:
    """
    Gets environment variables depending on active environment.
    """
    try:
        value = parse_env_value(os.environ[env_variable])
        return value
    except KeyError:
        error_msg = f'{env_variable} environment variable not set.'
        raise Exception(error_msg)


def parse_env_value(value: str) -> str | bool | int | None:
    """
    Parses environment variable into either bool, strings, ints, or None type.
    Defaults to string type.
    """ 
    if value == "none": return None             # checks for None type
    if value in ["0", "false"]: return False    
    if value in ["1", "true"]: return True
    if value.isnumeric(): return int(value)     
    return value