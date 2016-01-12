from bs4 import BeautifulSoup
import requests
from datetime import datetime
from selenium import webdriver
from time import sleep
from dateutil.parser import parse

__author__ = 'K R Prajwal'

class Tracker(object):
	'''
		This class contains the common features of each of the below trackers
		Each has the following Attributes:
			tracking_no: Tracking number of the shipment
			page: Raw HTML data of the page
			tracking_data: A list of checkpoints of the shipment
			status: The current/overall status of the shipment
	'''
	def __init__(self,tracking_no):
		'''
			Returns a Scraper Object containing the above Attributes
		'''
		self.tracking_no = str(tracking_no)
		self.page = None
		self.tracking_data = []
		self.status = None

	def Get_Tracking_Data(self):
		'''
			Helper function to get the tracking_data
		'''

		self.Get_Page()
		self.Extract_Checkpoints()

class BluedartTracker(Tracker):
	'''
		This class scrapes tracking data from the bluedart website.
	'''
	exclude_list = ['Location','Date','Waybill','Details','No.']

	def __init__(self,tracking_no):
		Tracker.__init__(self,tracking_no)

	def Get_Page(self):
		'''
			Fetches raw HTML data from the site for a given tracking_no
		'''

		url = 'http://www.bluedart.com/servlet/RoutingServlet'
		data = {'handler' : 'tnt',
		          'action' : 'awbquery',
		          'awb' : 'awb' ,
		          'numbers' : self.tracking_no}

		# request the server for the HTML data
		response = requests.post(url,data=data,verify=False)
		self.page = response.content

	def is_valid(self,text):
		for unwanted in self.exclude_list:
			if text is None or unwanted in text:
				return False
		return True

	def Extract_Checkpoints(self):
		'''
			Extract the checkpoints and store in self.tracking_data
		'''

		# Make sure page is available
		if self.page is None:
			raise Exception("The HTML data was not fetched due to some reasons")

		# Check for invalid tracking number
		if 'Numbers Not Found -'in self.page or 'Invalid Query Numbers -' in self.page:
			raise ValueError('The Tracking number is invalid')

		soup = BeautifulSoup(self.page,'html.parser')

		# Assign the current status of the shipment
		if 'Returned To Origin' in self.page:		 # Prioritise this first
			self.status = 'R'
		elif 'SHIPMENT DELIVERED' in self.page:	 # If the above is false, only then check for this
			self.status = 'C'
		else:											 # The shipment is in Transit
			self.status = 'T'						

		# Checkpoints extraction begins here 
		cells = []

		'''
			The below for loop goes through the table of checkpoints adding relevant cell data to cells[]
		'''

		for cell in soup.findAll('td', {"align" : "LEFT"}):
		    if cell.font["size"] == '1':
		    	cell_text = cell.font.string
		    	if self.is_valid(cell_text):
		    		cells.append(cell_text)

		# 4 cells in each row
		rows = [cells[cell:cell + 4] for cell in xrange(0, len(cells), 4)]

		for row in rows:

			'''
				Each row will have 4 columns: Location--Status--Date--Time
				Merge column three and four and format it. 
				Append to tracking_data list
			'''

			location = row[0]
			status = row[1]
			date_time = ' '.join((row[2],row[3]))
			date_time_format = "%d-%b-%Y %H:%M"
			date_time = datetime.strptime(date_time,date_time_format)

			self.tracking_data.append({'status':status,'date':date_time,'location':location})

		# Sort the checkpoints based on Date and Time --- this is important
		self.tracking_data = sorted(self.tracking_data, key=lambda k: k['date'])

class AramexTracker(Tracker):
	'''
	    This class scrapes data from the Aramex website    	
	'''
	def __init__(self, tracking_no):
		Tracker.__init__(self,tracking_no)

	def wait_till_page_load(self,driver,max_wait_time):
		'''
			This method pauses execution until the page is loaded fully, including
			data delayed by JavaScript
		'''
		sleepCount = max_wait_time		# wait for a fixed max_wait_time only 

		# A page that's fully loaded has the word 'Current Status'

		while 'Current Status' not in driver.page_source:		
			sleep(1)
			sleepCount -= 1
			if sleepCount is 0:
				raise Exception('Request timed out!')		# if max_wait_time is exceeded!

	def remove_non_ascii(self,str_to_clean):				
		return ''.join([x for x in str_to_clean if ord(x) < 128])

	def Get_Page(self):
		'''
			Fetches raw HTML data from the site for a given tracking_no
		'''

		# Simply encode the correct url as a string
		url = 'https://www.aramex.com/express/track-results-multiple.aspx?ShipmentNumber='
		url += self.tracking_no

		driver = webdriver.PhantomJS()			# create a selenium webdriver
		driver.get(url)							# make it send a request with the above url
		self.wait_till_page_load(driver,10)		# wait till the page is fully loaded
		self.page = driver.page_source		# store the html source
		driver.quit()							# stop the webdriver

	def Extract_Checkpoints(self):
		'''
			Extract the checkpoints and store in self.tracking_data
		'''

		# Make sure page is available
		if self.page is None:
			raise Exception("The HTML data was not fetched due to some reasons")

		# Check for invalid tracking number
		if 'Invalid number / data not currently available' in self.page:
			raise ValueError('Invalid number/data not currently available')

		# Checkpoints extraction begins here 
		
		soup = BeautifulSoup(self.page,'html.parser')
		
		# Assign the current status of the shipment - self.status

		current_status = soup.find('span',id='spnCurrentStatusValue').text.strip()
		if current_status == 'Supporting Document Returned to Shipper':	
			self.status = 'R'
		elif current_status == 'Delivered':
			self.status = 'C'
		else:											 # The shipment is in Transit
			self.status = 'T'

		# Get all rows of the Checkpoints table (no particular order)
		rows = soup.findAll('div',{'class':'fullWidth odd leftFloat bottomGreyBorder'})
		rows += soup.findAll('div',{'class':'fullWidth even leftFloat bottomGreyBorder'})

		for row in rows:
			# Get the data

			location = row.find('div',{'class':'leftFloat thirdWidth'}).string.strip()
			date_time = row.find('div',{'class':'leftFloat shipmentSummaryLabel'}).string.strip()
			status = row.find('div',{'class':'leftFloat shipmentHistoryActivityLabel'}).string.strip()

			# Clean it
			location = self.remove_non_ascii(location)
			date_time_format = "%d-%b-%Y %H:%M"
			date_time = parse(self.remove_non_ascii(date_time))
			status = self.remove_non_ascii(status)

			# Add it to the checkpoint list
			self.tracking_data.append({'status':status,'date':date_time,'location':location})

		self.tracking_data = sorted(self.tracking_data, key=lambda k: k['date'])

class DHLTracker(Tracker):
	'''
	    This class scrapes data from the DHL website    	
	'''

	def __init__(self, tracking_no):
		Tracker.__init__(self,tracking_no)

	def wait_till_page_load(self,driver,max_wait_time):
		'''
			This method pauses execution until the page is loaded fully, including
			data delayed by JavaScript
		'''
		sleepCount = max_wait_time		# wait for a fixed max_wait_time only 

		# A page that's fully loaded has the word 'Current Status'

		while self.tracking_no not in driver.page_source and 'Invalid Input' not in driver.page_source:		
			sleep(1)
			sleepCount -= 1
			if sleepCount is 0:
				raise Exception('Request timed out!')		# if max_wait_time is exceeded!

	def Get_Page(self):
		'''
			Fetches raw HTML data from the site for a given tracking_no
		'''

		# Simply encode the correct url as a string
		url = 'http://www.dhl.co.in/en/express/tracking.html?AWB={}&brand=DHL'.format(self.tracking_no)

		driver = webdriver.PhantomJS()			# create a selenium webdriver
		driver.get(url)							# make it send a request with the above url
		self.wait_till_page_load(driver,10)		# wait till the page is fully loaded
		self.page = driver.page_source		# store the html source
		driver.quit()							# stop the webdriver

	def Extract_Checkpoints(self):
		'''
			Extract the checkpoints and store in self.tracking_data
		'''

		# Make sure page is available
		if self.page is None:
			raise Exception("The HTML data was not fetched due to some reasons")

		soup = BeautifulSoup(self.page,'html.parser')

		# Check for invalid tracking number by checking if table element is present
		if soup.find('thead') == None:
			raise ValueError('Invalid tracking number')

		
		# Assign the current status of the shipment - self.status

		if 'Returned' in self.page:	
			self.status = 'R'
		elif 'Signed for by:' in self.page:
			self.status = 'C'
		else:											 # The shipment is in Transit
			self.status = 'T'

		# The full checkpoints table div.
		table = soup.find('table',{'class':'result-checkpoints'}).contents
		cur_date = None		# The date of the next few checkpoints, initially None
		checkpoint = None

		for element in table:
			if element.name == 'thead':
				# This has the date for the next few checkpoints
				cur_date = element.find('th',{'colspan':'2'}).string.strip() + ' '

			elif element.name == 'tbody':
				# A checkpoint whose date = cur_date
				checkpoint = {'status':'','date':cur_date,'location':''}
				tds = element.findAll('td')
				checkpoint['status'] = tds[1].string.strip()
				checkpoint['location'] = tds[2].string.strip()
				checkpoint['date'] += tds[3].string.strip()
				date_time_format = "%d-%b-%Y %H:%M"
				checkpoint['date'] = parse(checkpoint['date'])
				self.tracking_data.append(checkpoint)

		self.tracking_data = sorted(self.tracking_data, key=lambda k: k['date'])

class Skynet_Tracker(Tracker):
	'''
		This class scrapes tracking data from the Skynet website.
	'''

	def __init__(self,tracking_no):
		Tracker.__init__(self,tracking_no)

	def Get_Page(self):
		'''
			Fetches raw HTML data from the site for a given tracking_no
		'''

		url = 'https://www.skynetwwe.info/ShipmentTrackSingle.aspx?textfield={}&radiobutton=SB'.format(self.tracking_no)

		headers = {
					'Host': 'www.skynetwwe.info',
					'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:42.0) Gecko/20100101 Firefox/42.0',
					'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
					'Accept-Language': 'en-US,en;q=0.5',
					'Accept-Encoding': 'gzip, deflate',
					'DNT': '1',
					'Cookie': 'ASP.NET_SessionId=aletb2fx1kqixq55kmblbvn4',
					'Connection': 'keep-alive',
					'Cache-Control': 'max-age=0'
				   }
		
		# request the server for the HTML data
		response = requests.post(url,headers=headers,verify=False)
		self.page = response.content

	def Extract_Checkpoints(self):
		'''
			Extract the checkpoints and store in self.tracking_data
		'''

		# Make sure page is available
		if self.page is None:
			raise Exception("The HTML data was not fetched due to some reasons")

		soup = BeautifulSoup(self.page,'html.parser')

		invalid_tracking_no = soup.find('span',{'id':'ctl00_ContentPlaceHolder1_lblsMsg','class':'ErrorMessage','style':'font-family:Calibri;font-size:9pt;font-weight:bold;','name':'lblsMsg'})
		if invalid_tracking_no is not None:
			raise ValueError('The Tracking number is invalid')

		# Assign the current status of the shipment

		if 'Delivered' in self.page:
			self.status = 'C'
		else:											 # The shipment is in Transit
			self.status = 'T'						

		# Checkpoints extraction begins here 
		
		rows = soup.findAll('tr',{'class':'gridItem'}) + soup.findAll('tr',{'class':'gridAltItem'})

		for row in rows:

			'''
				Each row will have 4 columns: Date--Time--Status--Location
				Merge column one and two and format it. 
				Append to tracking_data list
			'''
			row_cells = row.findAll('td')

			date = row_cells[0].string.strip()
			time = row_cells[1].string.strip()
			date_time = ' '.join([date,time])
			date_time_format = "%d %b %Y %H:%M"
			date_time = datetime.strptime(date_time,date_time_format)
			status = row_cells[2].string.strip()
			location = row_cells[3].string.strip()
			
			self.tracking_data.append({'status':status,'date':date_time,'location':location})

		# Sort the checkpoints based on Date and Time --- this is important
		self.tracking_data = sorted(self.tracking_data, key=lambda k: k['date'])

class Overnite_Tracker(Tracker):
	'''
		This class scrapes tracking data from the Overnite express website.
	'''

	def __init__(self,tracking_no):
		Tracker.__init__(self,tracking_no)

	def Get_Page(self):
		'''
			Fetches raw HTML data from the site for a given tracking_no
		'''

		url = 'http://www.overnitenet.com/Web-Track.aspx'

		data = {
			'__EVENTTARGET':'',
			'__EVENTARGUMENT':'',
			'__VIEWSTATE':'/wEPDwUKLTY0MDE3NTA3NWQYAQUeX19Db250cm9sc1JlcXVpcmVQb3N0QmFja0tleV9fFgQFFWN0bDAwJENvbnRlbnQkcmRBd2JObwUVY3RsMDAkQ29udGVudCRyZFJlZk5vBRVjdGwwMCRDb250ZW50JHJkUmVmTm8FGWN0bDAwJENvbnRlbnQkaW1nYnRuVHJhY2uCRZzZgz3GDGJ/LncXvzFMpEh90g==',
			'__EVENTVALIDATION':'/wEWBgKc68neCQLx5f2jAQKYpPrsCgKcioujBgL2vJr6BALJ97buCl91xQYFzc1Hb3E2f/BkGHccMKCx',
			'ctl00$Content$rb':'rdAwbNo',
			'ctl00$Content$txtAWB':self.tracking_no,
			'ctl00$Content$ValidatorCalloutExtender6_ClientState':'',
			'ctl00$Content$imgbtnTrack.x':'28',
			'ctl00$Content$imgbtnTrack.y':'8'
		}

		headers = {
			'Host': 'www.overnitenet.com',
			'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:43.0) Gecko/20100101 Firefox/43.0',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			'Accept-Language': 'en-US,en;q=0.5',
			'Accept-Encoding': 'gzip, deflate',
			'DNT': '1',
			'Referer': 'http://www.overnitenet.com/Web-Track.aspx',
			'Cookie': 'ASP.NET_SessionId=3ncsag55xq0z4vqltg3egbr4',
			'Connection': 'keep-alive'
		}

		# request the server for the HTML data
		response = requests.post(url,data=data,headers=headers,verify=False)

		self.page = response.content

	def Extract_Checkpoints(self):
		'''
			Extract the checkpoints and store in self.tracking_data
		'''

		# Make sure page is available
		if self.page is None:
			raise Exception("The HTML data was not fetched due to some reasons")

		soup = BeautifulSoup(self.page,'html.parser')

		if 'Delivery information not found' in self.page:
			raise ValueError('The Tracking number is invalid/Tracking number is over 45 days old.')

		# Assign the current status of the shipment

		if 'Delivered on' in self.page:
			self.status = 'C'
		else:											 # The shipment is in Transit
			self.status = 'T'						

		# Checkpoints extraction begins here 
		
		table = soup.findAll('table',{'cellpadding':'1','cellspacing':'1','border':'1','align':'center','style':"width:800px;border-color:#034291;"})[1]
		rows = table.findAll('tr')[1:]

		for row in rows:

			'''
				Each row will have 3 columns: Date--Location--Status
			'''
			row_cells = row.findAll('td')
			date = row_cells[0].string.strip()
			date = datetime.strptime(date,"%A, %B %d, %Y")
			location = row_cells[1].find('a').string.strip()
			if location is '':		# ignore the days which are holidays
				continue
			status = row_cells[2].text.strip()
			
			self.tracking_data.append({'status':status,'date':date,'location':location})

		# Sort the checkpoints based on Date and Time --- this is important
		self.tracking_data = sorted(self.tracking_data, key=lambda k: k['date'])

class Ecomm_Tracker(Tracker):
	'''
		This class scrapes tracking data from the Ecomm express website.
	'''

	def __init__(self,tracking_no):
		Tracker.__init__(self,tracking_no)

	def Get_Page(self):
		'''
			Fetches raw HTML data from the site for a given tracking_no
		'''

		url = 'https://billing.ecomexpress.in/track_me/multipleawb_open/?awb={}&order=&news_go=track+now'.format(self.tracking_no)
		data = {
			'awb':self.tracking_no,
			'order':'',
			'news_go':'track_now'
		}

		headers = {
			'Host': 'billing.ecomexpress.in',
			'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:43.0) Gecko/20100101 Firefox/43.0',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			'Accept-Language': 'en-US,en;q=0.5',
			'Accept-Encoding': 'gzip, deflate',
			'DNT': '1',
			'Connection': 'keep-alive'
		}

		# request the server for the HTML data
		response = requests.get(url,data=data,headers=headers,verify=False)

		self.page = response.content

	def Extract_Checkpoints(self):
		'''
			Extract the checkpoints and store in self.tracking_data
		'''

		# Make sure page is available
		if self.page is None:
			raise Exception("The HTML data was not fetched due to some reasons")

		# use a different parser, page contains broken HTML
		soup = BeautifulSoup(self.page,'html5lib') 

		if self.tracking_no not in self.page:
			raise ValueError('The Tracking number is invalid.')

		# Assign the current status of the shipment
		table = soup.find('table',{'class':'table'}).find('tbody')
		rows = table.findAll('tr')

		present_status = rows[0].findAll('td')[1].text.strip()
		if present_status is 'Delivered':
			self.status = 'C'
		elif 'Shipment Redirected under' in present_status:
			self.status = 'R'
		else:										# If not the above two, then the shipment is in Transit
			self.status = 'T'						

		# Checkpoints extraction begins here 

		for row in rows:
			'''
				Each row will have 2 columns: (Date|Time, Location) --- (Status)
			'''
			row_cells = row.findAll('td')
			date,location = row_cells[0].string.strip().split(' ,  ')
			date = datetime.strptime(date,"%d-%m-%Y | %H:%M:%S")
			status = row_cells[1].text.strip()
			
			self.tracking_data.append({'status':status,'date':date,'location':location})

		# Sort the checkpoints based on Date and Time --- this is important
		self.tracking_data = sorted(self.tracking_data, key=lambda k: k['date'])

class Gati_Tracker(Tracker):
	'''
		This class scrapes tracking data from the Gati website.
	'''

	def __init__(self,tracking_no):
		Tracker.__init__(self,tracking_no)

	def Get_Page(self):
		'''
			Fetches raw XML data from the site for a given tracking_no
		'''
		url = 'http://www.gati.com/webservices/gatiicedkttrack.jsp?dktno=' + self.tracking_no
		response = requests.get(url)

		self.page = response.text

	def Extract_Checkpoints(self):
		'''
			Extract the checkpoints and store in self.tracking_data
		'''
		soup = BeautifulSoup(self.page,'xml')

		if soup.find('result').string.strip() == 'failed':
			raise ValueError('The Tracking number is invalid.')

		status = soup.find('DOCKET_STATUS').string.strip()

		if status == 'Delivered':
			self.status = 'C'
		elif status == 'Rebooked':
			self.status = 'R'
		else:
			self.status = 'T'

		# Checkpoints extraction begins here
		rows = soup.findAll('ROW')

		for row in rows:
			'''
				Each row has four columns:
					date --- time --- location --- status
				Merge #1 and #2
				Append the 3 to self.tracking_data
			'''
			date = row.find('INTRANSIT_DATE').string.strip()
			time = row.find('INTRANSIT_TIME').string.strip()
			try:
				location = row.find('INTRANSIT_LOCATION').string.strip()
			except AttributeError:
				location = ''
			status = row.find('INTRANSIT_STATUS').string.strip()
			date_time = datetime.strptime(' '.join([date,time]),"%d-%b-%Y %H:%M")

			self.tracking_data.append({'status':status,'date':date_time,'location':location})

		# Sort the checkpoints based on Date and Time --- this is important
		self.tracking_data = sorted(self.tracking_data, key=lambda k: k['date'])

# 7 trackers defined till now! 
