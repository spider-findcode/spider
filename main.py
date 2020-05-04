from bs4 import BeautifulSoup
import requests
import urllib3
import json
import time
from time import sleep
import xlsxwriter
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.mime.application import MIMEApplication

class github_crawl():

	def __init__(self):
		# 初始化一些必要的参数
		self.login_headers = {
			"Referer": "https://github.com/",
			"Host": "github.com",
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36"
		}
 
		self.logined_headers = {
			"Referer": "https://github.com/login",
			"Host": "github.com",
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36"
		}

		self.login_url = "https://github.com/login"
		self.post_url = "https://github.com/session"
		requests.adapters.DEFAULT_RETRIES = 5 # 增加重连次数
		self.session = requests.session()
		self.session.verify = False
		self.session.keep_alive = False
		urllib3.disable_warnings()

		# 爬取结果生成文件
		self.date = time.strftime("%Y%m%d", time.localtime())
		self.github_json = {}
		self.path_github_json = "./github-spider.json"
		self.path_github_xls = "./github-spider-" + self.date + ".xls"
		self.workbook = xlsxwriter.Workbook(self.path_github_xls)
 
	def parse_loginPage(self):
		# 对登陆页面进行爬取，获取token值
		html = self.session.get(url=self.login_url, headers=self.login_headers, verify=False)
		Soup = BeautifulSoup(html.text, "lxml")
		token = Soup.find("input", attrs={"name": "authenticity_token"}).get("value")
		return token
 
	def login(self, user_name, password,keywords):
		# 传进必要的参数，然后登陆
		post_data = {
			"commit": "Sign in",
			"utf8": "✓",
			"authenticity_token": self.parse_loginPage(),
			"login": user_name,
			"password": password
		}
		
		logined_html = self.session.post(url=self.post_url, data=post_data, headers=self.logined_headers, verify=False)
		if logined_html.status_code == 200:
			request_Flag = False;

			# 遍历检索关键字
			for keyword in keywords:
				repositories_total_count = self.parse_repositories(keyword)  # 检索repositories
				users_total_count = self.parse_users(keyword)
				commits_total_count = self.parse_commits(keyword)

				data = {"repositories": {"last_total_count":0, "total_count": repositories_total_count},
						"users": {"last_total_count":0, "total_count": users_total_count},
						"commits": {"last_total_count":0, "total_count": commits_total_count},
						"file_name": self.path_github_xls,
						"date": self.date}
				self.github_json[keyword] = data

				if isinstance(repositories_total_count,int) & isinstance(users_total_count,int) & isinstance(commits_total_count,int):
					request_Flag = True
			
			if request_Flag:
				self.send_mail()

		self.workbook.close()
		self.session.close()


	# 通过github api检索repositories名称或描述匹配关键字
	def parse_repositories(self, keyword):
			try:
				url = "https://api.github.com/search/repositories?q={keyword}&sort=updated&o=desc".format(keyword=keyword)
				resp = self.session.get(url, verify=False)
				repositorysJson = json.loads(resp.text)
				total_count = repositorysJson['total_count']
				if total_count > 0:

					# 结果写excel
					sheet = self.workbook.add_worksheet(keyword + "_repositorys")

					# 写表头
					head = ['full_name','html_url','description','created_at','updated_at']
					for h in range(len(head)):
						sheet.write(0, h, head[h])
					# 写数据
					row = 1
					for item in repositorysJson['items']:
					    sheet.write(row, 0, item['full_name'])
					    sheet.write(row, 1, item['html_url'])
					    sheet.write(row, 2, item['description'])
					    sheet.write(row, 3, item['created_at'])
					    sheet.write(row, 4, item['updated_at'])
					    row += 1
					    
					# 保存工作簿
					print(keyword + "_repositories_xls格式表格写入数据成功！")

				return total_count

			except Exception as e:
				print(e)


	# 通过github api检索users名称或描述匹配关键字
	def parse_users(self, keyword):
			try:
				url = "https://api.github.com/search/users?q={keyword}&sort=joined".format(keyword=keyword)
				resp = self.session.get(url, verify=False)
				usersJson = json.loads(resp.text)
				total_count = usersJson['total_count']

				if total_count > 0:

					# 结果写excel
					sheet = self.workbook.add_worksheet(keyword + "_users")

					# 写表头
					head = ['user_name','html_url']
					for h in range(len(head)):
						sheet.write(0, h, head[h])

					# 写数据
					row = 1
					for item in usersJson['items']:
					    sheet.write(row, 0, item['login'])
					    sheet.write(row, 1, item['html_url'])
					    row += 1
					    
					# 保存工作簿
					print(keyword + "_users_xls格式表格写入数据成功！")

				return total_count

			except Exception as e:
				print(e)


	# 通过github api检索commits名称或描述匹配关键字
	def parse_commits(self, keyword):
			try:
				headers = {
				    'Accept': 'application/vnd.github.cloak-preview'
				}
				url = "https://api.github.com/search/commits?q={keyword}&sort=committer-date".format(keyword=keyword)
				resp = self.session.get(url, verify=False, headers=headers)
				commitsJson = json.loads(resp.text)
				total_count = commitsJson['total_count']

				if total_count > 0:

					# 结果写excel
					sheet = self.workbook.add_worksheet(keyword + "_commits")

					# 写表头
					head = ['full_name','html_url','description','committer','date']
					for h in range(len(head)):
						sheet.write(0, h, head[h])

					# 写数据
					row = 1
					for item in commitsJson['items']:
					    sheet.write(row, 0, item['repository'].get('full_name'))
					    sheet.write(row, 1, item['html_url'])
					    sheet.write(row, 2, item['repository'].get('description'))
					    sheet.write(row, 3, item['commit'].get('committer').get('name'))
					    sheet.write(row, 4, item['commit'].get('committer').get('date'))
					    row += 1
					    
					# 保存工作簿
					print(keyword + "_commits_xls格式表格写入数据成功！")

				return total_count

			except Exception as e:
				print(e)



 	# 发送邮件
	def send_mail(self):
		# 第三方 SMTP 服务
		mail_host="smtp.163.com"  #设置服务器
		mail_user="XXX@163.com"    #用户名
		mail_pass="*********"   #口令
		
		sender = 'XXX@163.com'   # 发送邮箱地址
		to_receivers = ['XXX@163.com','XXX@163.com'] # 接收邮箱地址
		cc_receivers = ['XXX@163.com']
		receivers = to_receivers + cc_receivers
		
		message = MIMEMultipart()

		message['From'] =  sender
		message['To'] = ";".join(to_receivers)
		message['CC'] = ";".join(cc_receivers)

		subject = 'github关键字抓取情况_'+time.strftime("%Y%m%d", time.localtime())
		message['Subject'] = Header(subject, 'utf-8')
		
		# 加载昨日/上次json
		last_github_json_file = open(self.path_github_json, encoding='utf-8')
		last_github_json = json.load(last_github_json_file)
		# self.github_json = last_github_json  # 测试邮件用
		
		# 邮件正文
		mail_msg = """
			<p>Github关键字排查情况</p>
			"""

		for item in self.github_json.items():

			mail_msg +=	"""
				<p>关键字：%(keyword)s （<a>https://github.com/search?o=desc&q=%(keyword)s&s=updated&type=Repositories</a>）<br>
				1.repositories（仓库）：今日共%(repos)s条记录，昨日共%(last_repos)s条记录 <br>
				2.users（用户）：今日共%(users)s条记录，昨日共%(last_users)s条记录 <br>
				3.commits（提交）：今日共%(commits)s条记录，昨日共%(last_commits)s条记录 <br>
				</p>
				""" % dict(keyword=item[0],
					repos=item[1]["repositories"]["total_count"], last_repos=last_github_json[item[0]]["repositories"]["total_count"],
					users=item[1]["users"]["total_count"], last_users=last_github_json[item[0]]["users"]["total_count"],
					commits=item[1]["commits"]["total_count"], last_commits=last_github_json[item[0]]["commits"]["total_count"])
		
		message.attach(MIMEText(mail_msg, 'html', 'utf-8'))
		
		# 构造附件1，传送当前目录下的github_xls文件
		att1 = MIMEApplication(open(self.path_github_xls, 'rb').read())
		att1["Content-Type"] = 'application/octet-stream'
		att1.add_header('Content-Disposition','attachment',filename=self.path_github_xls)
		message.attach(att1)

		try:
			smtpObj = smtplib.SMTP_SSL(mail_host, 465) 
			smtpObj.login(mail_user,mail_pass)
			smtpObj.sendmail(sender, receivers, message.as_string())
			print ("邮件发送成功")
		except Exception as e:
			print(e)

		
		# 更新json结果写文件
		try:
			jsObj = json.dumps(self.github_json)
			with open(self.path_github_json,"w") as fw:
				fw.write(jsObj)
				fw.close()
		except Exception as e:
			print(e)


if __name__ == "__main__":
	x = github_crawl()
	x.login("github_username", "github_password", ["keyword1", "keyword2"])
