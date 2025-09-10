#%%
from decouple import config
import jwt
import time
import requests

#%%


SUPABASE_URL = config('SUPABASE_URL')
SUPABASE_KEY = config('SUPABASE_KEY')



#%%