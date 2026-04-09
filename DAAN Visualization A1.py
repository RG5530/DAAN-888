#!/usr/bin/env python
# coding: utf-8

# In[1]:


#pip install streamlit
import pandas as pd
#Load files
import numpy as np
import os



# In[6]:


# Upload datasets
os.chdir("C:/Users/rache/OneDrive/Documents/DAAN 888 - Analytics Des Imp (2026)")
#Final Monthly Data Rev9 (History and Forecast)
#import pandas as pd
Monthly_data = pd.read_csv ("testFinal Monthly Data Rev9 (History and Forecast) (2).csv")

#Predicaitons
#import pandas as pd
Predictions_data = pd.read_csv ("testpredictions.csv")

#Data View 
#import pandas as pd
View_data = pd.read_csv ("testView Data 1.csv")
View_data.head()
View_data.describe() #key values 
View_data.columns
View_data.rename(columns={'Zip_Code': 'Zip Code'}, inplace=True)


# In[7]:


#Monthly and View Data merged
merge1 = pd.merge(View_data, Monthly_data, on='Zip Code')
merge1.head()
merge1.describe() #key values 
merge1.columns
merge1.shape

#Remove unneccsary columns to find corr
#merge1 = merge1.drop('', axis =1)
#merge1 = merge1.drop('', axis =1)
#merge1 = merge1.drop('', axis =1)


# In[ ]:




