#### This repository contains tracking APIs written in Python for couriers shipped through major courier companies.

### How to use:
```python
>>> from trackers import BluedartTracker
>>> b = BluedartTracker([put tracking id here])
>>> b.Get_Tracking_Data()
```
> The tracking object would now contain the current status of the shipment, and the list of checkpoints of the shipment. Use it at your will!

#### Requirements:
    1. The delicious Requests library
    2. BeautifulSoup
    3. Selenium (only for a couple of courier companies)
    4. python-dateutil
    
To install them run: 
    
    pip install -r requirements.txt

> This was a portion of my work during my internship.
> I have open sourced it, so that it could be of any help to anyone on the web :)

