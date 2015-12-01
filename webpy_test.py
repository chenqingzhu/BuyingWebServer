# -*- coding: utf-8 -*-

import random
import string
import web
import json
import redis
#import MySQLdb
import psycopg2
import pymysql
from DBUtils import PooledDB
import os
import time 
import sys
db_host=os.getenv("DB_HOST", "localhost")
db_port=int(os.getenv("DB_PORT", 3306))
db_user=os.getenv("DB_USER", "root")
db_passwd=os.getenv("DB_PASS", "toor")
db_name=os.getenv("DB_NAME", "eleme")

app_host = os.getenv("APP_HOST","0.0.0.0")
app_port = os.getenv("APP_PORT",8080)

redis_host = os.getenv("REDIS_HOST","localhost")
redis_port = int(os.getenv("REDIS_PORT",6379))
python_path = os.getenv("PYTHONPATH")

#print db_user

pool = PooledDB.PooledDB(pymysql, port=db_port, host=db_host, database=db_name,user=db_user, password=db_passwd,mincached=2, maxconnections=30)
myredis = redis.Redis(host=redis_host,port = redis_port,db = 0)
redisPool = redis.ConnectionPool(host=redis_host,port = redis_port,db = 0)
redisconn = redis.Redis(connection_pool = redisPool)

food_id_list_key = "food_id_list"
order_list_key = "order_list_key"



urls = (
	'/login','login',
	'/foods','foods',
	'/carts','carts',
	'/order','order',
	'/orders','orders',
	'/admin/orders','admin_orders',
	'.*','addfood'
	)

app=web.application(urls,globals())

food_file = open("food_sql.txt",'w')
user_file = open("user_sql.txt",'w')

def write_file(f,content):
	for each in content:
		intofile = str(each) + (25-len(str(each)))* " "
		f.write(intofile)
	f.write("\n")
	return ""

    
def init_user_and_food_2_redis():
	print  time.ctime()
	conn = pool.connection()
	cur = conn.cursor()
	cur.execute("select id, name, password from user")
	userMsg = cur.fetchall()
	i=0
	redisconn = redis.Redis(connection_pool = redisPool)
	redisconn.flushdb()
	print "select mysql  ok   :",time.ctime()
	user_list = ["user_id", "user_name", "user_password" ]
	food_list = [ "food_id", "food_stock(数量)", "food_price" ]
	write_file(food_file,food_list)
	write_file(user_file,user_list)

	for user in userMsg:
		write_file(user_file,user)
		usernameKey = "user" + "_" + user[1]
		#print usernameKey
		if redisconn.exists(usernameKey):
			print "exists " + usernameKey
			redisconn.delete(usernameKey)
			continue
		# list: use_id, user_password, user_token
		redisconn.rpush(usernameKey,user[0],user[2],"")
		#print "push redis KEY:" +usernameKey +"    id: "+ str(user[0])+"   name:"+user[1] + "   password:"+user[2]
		i = i + 1

		#if i >5:
		#	break;
	print  "init_user_2_redis successful,total user number: " , i
	print  "init user ok: ",time.ctime()
	cur.execute("SELECT id, stock, price FROM food;")
	foodMsg = cur.fetchall()
	i = 0
	
	redisconn = redis.Redis(connection_pool = redisPool)
	for food in foodMsg:
		foodIdKey = "food_" + str(food[0])
		write_file(food_file,food)
		#print foodIdKey
		#food list: food_stock, food_price
		#redisconn.rpush(foodIdKey,food[1],food[2])
		redisconn.hset(foodIdKey,"stock",int(food[1]))
		redisconn.hset(foodIdKey,"price",(food[2]))
		#print "food information id: "+str(food[0]) + "   stock: "+ str(food[1]) + "   price: " + str(food[2])
		redisconn.rpush(food_id_list_key,food[0])
		i = i+1
		#if i >5:
		#	break;

	print "init_food_2_redis success,total food number : " ,i
	print  "init food ok : ",time.ctime()
	food_file.close()
	user_file.close()
	return ""




def get_random_string():
	conn = redis.Redis(connection_pool = redisPool)
	ret = string.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a','1','2','3','4','5','6','7','8','9'], 28)).replace(' ','')
	while(conn.exists(ret)):
		ret = string.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a','1','2','3','4','5','6','7','8','9'], 28)).replace(' ','')
	return ret

#登陆  －POST请求
#请求示例
class login:
	def GET(self):
		parameter  = web.input()
		u_name = str(parameter.get("username",""))
		pw = parameter.get("password","")
		conn = redis.Redis(connection_pool = redisPool)
		#print "u_name:",u_name
		#print "key:" ,"user_"+u_name
		if(u_name=="" or str(pw) ==""):
			ret = {"code": "EMPTY_REQUEST","message": "请求体为空"}	
		#	print "login get error", "  参数为空"
			web.ctx.status = '400 Bad Request'
			return json.dumps(ret)
		if not conn.exists("user_"+u_name):
			web.ctx.status = '403 Forbidden'
			#＃web.webapi.Forbidden(message=None)
			ret = {"code": "USER_AUTH_FAIL","message": "用户名或密码错误"}		
		#	print "login error", "  用户名不存在"
			web.ctx.status = '403 Forbidden'
			return json.dumps(ret);
		userMsg = conn.lrange("user_" + u_name,0,-1)
		#print "userMsg",userMsg
		if (userMsg[2] != "" and userMsg[1] == pw):
			retDict = {}
			retDict["user_id"] = userMsg[0]
			retDict["username"] = u_name
			retDict["access_token"] = userMsg[2]
		#	print u_name + "重复登陆，直接返回token:" +userMsg[2]
			return json.dumps(retDict)

		if(userMsg[1] == pw):
			retDict = {}
			retDict["user_id"] = userMsg[0]
			retDict["username"] = u_name
			#retDict["access_token"] = random.choice('abcdefghijklmnopqrstuvwxyz!@#$%^&*()')
			retDict["access_token"] = get_random_string()
			conn.rpush(str(retDict["access_token"]),userMsg[0],u_name)
			conn.lset("user_"+u_name,2,retDict["access_token"] )
			web.ctx.status = '200 OK'
			#print "after update user msg: " , conn.lrange("user_"+u_name,0,-1)
			#print u_name ," login  successful with token:" ,retDict["access_token"]
			return json.dumps(retDict)
		else:
			ret = {"code": "USER_AUTH_FAIL","message": "用户名或密码错误"}			
		#	print "login error 密码错误"
			web.ctx.status = '403 Forbidden'
			return json.dumps(ret);
	def POST(self):
		
		para_str = web.data()

		u_name = ""
		pw = ""
		#print "parameter:" ,para_str

		if(para_str != ""):
			try:
				parameter = json.loads(para_str)
				u_name = str(parameter.get("username",""))
				pw = str(parameter.get("password",""))
			except:
				ret = {"code": "MALFORMED_JSON","message": "格式错误"}	
		#		print "login error", "  json 格式错误"
				web.ctx.status = '400 Bad Request'
				return json.dumps(ret)
		else:
			ret = {"code": "EMPTY_REQUEST","message": "请求体为空"}	
		#	print "login error", "  request 请求体为空"
			web.ctx.status = '400 Bad Request'
			return json.dumps(ret)

		#if(u_name=="" or str(pw) ==""):
		#print "u_name:",u_name
		#print "key:" ,"user_"+u_name

		conn = redis.Redis(connection_pool = redisPool)
		if not conn.exists("user_"+u_name):
			ret = {"code": "USER_AUTH_FAIL","message": "用户名或密码错误"}		
		#	print "login error", "  用户名不存在"
			web.ctx.status = '403 Forbidden'
			return json.dumps(ret);

		
		userMsg = conn.lrange("user_" + u_name,0,-1)
		#print "userMsg",userMsg
		if (userMsg[2] != "" and userMsg[1] == pw):
			retDict = {}
			retDict["user_id"] = int(userMsg[0])
			retDict["username"] = u_name
			retDict["access_token"] = userMsg[2]
		#	print u_name + "重复登陆，直接返回token:" +userMsg[2]
			return json.dumps(retDict)

		if(userMsg[1] == pw):
			retDict = {}
			retDict["user_id"] = int(userMsg[0])
			retDict["username"] = u_name
			#retDict["access_token"] = random.choice('abcdefghijklmnopqrstuvwxyz!@#$%^&*()')
			retDict["access_token"] = get_random_string()
			conn.rpush(str(retDict["access_token"]),userMsg[0],u_name)
			conn.lset("user_"+u_name,2,retDict["access_token"] )
			web.ctx.status = '200 OK'
			#print "after update user msg: " , conn.lrange("user_"+u_name,0,-1)
			#print u_name ," login  successful with token:" ,retDict["access_token"]
			return json.dumps(retDict)
		else:
			ret = {"code": "USER_AUTH_FAIL","message": "用户名或密码错误"}			
		#	print "login error 密码错误"
			web.ctx.status = '403 Forbidden'
			return json.dumps(ret);
		#return ""

#查询库存
class  foods:
	def GET(self):
		#token 在参数parameter里
		parameter = web.input()
		access_token = str(parameter.get("access_token",""))
		#print "access_token 1: ",access_token

		#token 在参数parameter里
		if(access_token == ""):
			#print "parameter access_token is NULL"
			#print web.ctx.env
			access_token = web.ctx.env.get("HTTP_ACCESS_TOKEN","")
			#print "access_token 2: ",access_token
			if(access_token == ""):
				#print "headers access_token is NULL"
				ret = {"code": "INVALID_ACCESS_TOKEN","message": "无效的令牌"}	
		#		print "查询库存 error", "  token为空"
				web.ctx.status= '401 Unauthorized'
				return json.dumps(ret)

		conn = redis.Redis(connection_pool = redisPool)
		#print "access_token 3: ",access_token
		if not conn.exists(str(access_token)):
			ret = {"code": "INVALID_ACCESS_TOKEN","message": "无效的令牌"}	
		#	print "查询库存 error", "  token为空"
			web.ctx.status = '401 Unauthorized'
			return json.dumps(ret)

		#id_len = conn.llen(food_id_list_key)

		id_list = conn.lrange(food_id_list_key,0,-1)
		#print "物品数：", len(id_list)
		ret = []
		for id in id_list:
			#foodMsg = conn.lrange("food_"+str(id),0,-1)
			dic = {"id": int(id), "price": int(conn.hget("food_"+str(id),"price")), "stock": int(conn.hget("food_"+str(id),"stock")) }
			ret.append(dic)
		#print ret[0:10]
		web.ctx.status = '200 OK'
		return json.dumps(ret)
		#return ""

#创建篮子
class carts:
	def POST(self):
		para_str = web.data()
		#print "parameter:" ,para_str
		access_token = ""
		conn = redis.Redis(connection_pool = redisPool)
		#token 在body里
		'''
		if(not (para_str == "")):
			parameter = json.loads(para_str)
			access_token = str(parameter.get("access_token",""))
		'''
		#token 在参数parameter里
		if(access_token == ""):
			parameter123 = web.input()
			#print "parameter123:", parameter123
			access_token = str(parameter123.get("access_token",""))

		#token 在header里
		if(access_token == "" ):
			#print "parameter access_token is NULL"
			#print web.ctx.env
			access_token = web.ctx.env.get("HTTP_ACCESS_TOKEN","")
			#print "access_token 2: ",access_token
			if(access_token == "" or (not conn.exists(str(access_token)))):
				#print "headers access_token is NULL"
		#		print "创建篮子 error", "  token为空"
				ret = {"code": "INVALID_ACCESS_TOKEN","message": "无效的令牌"}	
				web.ctx.status = '401 Unauthorized'
				return json.dumps(ret)

		#print "创建篮子token: ",access_token
		userMsg = conn.lrange(str(access_token),0,-1)

		cartId = get_random_string()

		conn.rpush(cartId,userMsg[0],userMsg[1],str(access_token))
		web.ctx.status = '200 OK'
		ret = {"cart_id": cartId}
		return json.dumps(ret)

class addfood:
	def PATCH(self):
		#print "into patch"
		#print web.ctx.env
		url = web.ctx.env.get("REQUEST_URI","")
		carts_id = url.split('?')[0].split('/')[-1]	
		#print "usr: ",url
		#print "carts_id: ",carts_id
		conn = redis.Redis(connection_pool = redisPool)
		if(not conn.exists(carts_id)):
			ret = {"code": "CART_NOT_FOUND","message": "篮子不存在"}	
		#	print "添加购物车 error", "  篮子不存在"
			web.ctx.status = '404 Not Found'
			return json.dumps(ret)

		access_token = ""
		#token 在参数parameter里
		if(access_token == ""):
			parameter123 = web.input()
			#print "parameter123:", parameter123
			access_token = str(parameter123.get("access_token",""))
		#token 在header里
		if(access_token == ""):
			#print "parameter access_token is NULL"
			#print web.ctx.env
			access_token = web.ctx.env.get("HTTP_ACCESS_TOKEN","")
			#print "access_token 2: ",access_token
			if(access_token == "" or (not conn.exists(str(access_token))) ):
		#		print "添加购物车 error", "  token为空"
				ret = {"code": "INVALID_ACCESS_TOKEN","message": "无效的令牌"}	
				web.ctx.status = '401 Unauthorized'
				return json.dumps(ret)

		body_str = web.data()
		food_id = -1
		food_connt = -1;
		if(body_str != ""):
			try:
				body_para = json.loads(body_str)
				food_id = str(body_para.get("food_id",""))
				food_count = str(body_para.get("count",""))
			except:
				ret = {"code": "MALFORMED_JSON","message": "格式错误"}	
		#		print "添加购物车 error", "  json 格式错误"
				web.ctx.status = '400 Bad Request'
				return json.dumps(ret)
		else:
			ret = {"code": "EMPTY_REQUEST","message": "请求体为空"}	
		#	print "添加购物车 error", "  request 请求体为空"
			web.ctx.status = '400 Bad Request'
			return json.dumps(ret)

		#print "food_id: ",food_id
		#print "count: ",food_count

		if(not conn.exists("food_" + (food_id) ) ):
			ret = {"code": "FOOD_NOT_FOUND","message": "食物不存在"}	
		#	print "添加购物车 error", "  食物不存在 "
			web.ctx.status = '404 Not Found'
			return json.dumps(ret)

		cartsMsg = conn.lrange(carts_id,0,-1)
		if(cartsMsg[2] != access_token):
			ret = {"code": "NOT_AUTHORIZED_TO_ACCESS_CART","message": "无权限访问指定的篮子"}	
		#	print "添加购物车 error", "  无权限访问指定的篮子"
			web.ctx.status = '401 Unauthorized'
			return json.dumps(ret)

		#验证篮子中是否已经有带加入的food_id
		##cartsMsg = conn.lrange(carts_id,0,-1)
		#print "len: ", len(cartsMsg)
		if len(cartsMsg) > 3:
			for i in range(3,len(cartsMsg)):
				dicts = cartsMsg[i].split('_')
		#		print "dicts:",dicts
				if(int(food_id) == int(dicts[0])):
					tmp_str = str(dicts[0]) + "_" + str(int(dicts[1]) + int(food_count))
					conn.lset(carts_id,i,tmp_str)
		#			print "add ok"
					web.ctx.status = '204 No content'
					return ""
		if(len(cartsMsg) >= 6):
			ret = {"code": "FOOD_OUT_OF_LIMIT","message": "篮子中食物数量超过了三个"}	
		#	print "添加购物车 error", "  篮子中食物数量超过了三个"
			web.ctx.status = '403 Forbidden'
			return json.dumps(ret)

		foodMsg =str(food_id) + "_" + str(food_count)
		conn.rpush(carts_id,foodMsg)
		#print "insert ok"
		web.ctx.status = '204 No content'
		return ""

#下单及查询
class orders:
	#下单
	def POST(self):
		para_str = web.data()
		carts_id = ""
		#print "parameter:" ,para_str

		conn = redis.Redis(connection_pool = redisPool)
		if(para_str != ""):
			try:
				parameter = json.loads(para_str)
				carts_id = str(parameter.get("cart_id",""))
				#pw = str(parameter.get("password",""))
			except:
				ret = {"code": "MALFORMED_JSON","message": "格式错误"}	
		#		print "下单 error", "  json 格式错误"
				web.ctx.status = '400 Bad Request'
				return json.dumps(ret)
		else:
			ret = {"code": "EMPTY_REQUEST","message": "请求体为空"}	
		#	print "下单 error", "  request 请求体为空"
			web.ctx.status = '400 Bad Request'
			return json.dumps(ret)

		access_token = ""
		#token 在参数parameter里
		if(access_token == ""):
			parameter123 = web.input()
			#print "parameter123:", parameter123
			access_token = str(parameter123.get("access_token",""))

		#token 在header里
		if(access_token == ""):
			#print "parameter access_token is NULL"
			#print web.ctx.env
			access_token = web.ctx.env.get("HTTP_ACCESS_TOKEN","")
			#print "access_token 2: ",access_token
			if(access_token == "") or (not conn.exists(access_token)):
				#print "headers access_token is NULL"
		#		print "下单 error", "  token为空"
				ret = {"code": "INVALID_ACCESS_TOKEN","message": "无效的令牌"}	
				web.ctx.status = '401 Unauthorized'
				return json.dumps(ret)

		if( not conn.exists(carts_id)):
			ret = {"code": "CART_NOT_FOUND","message": "篮子不存在"}	
		#	print "下单 error", "  篮子不存在"
			web.ctx.status = '404 Not Found'
			return json.dumps(ret)

		cartMsg = conn.lrange(carts_id,0,-1)

		if(cartMsg[2] != access_token):
			ret = {"code": "NOT_AUTHORIZED_TO_ACCESS_CART","message": "无权限访问指定的篮子"}	
		#	print "下单 error", "  无权限访问指定的篮子"
			web.ctx.status = '401 Unauthorized'
			return json.dumps(ret)

		if(len(conn.lrange("user_"+cartMsg[1],0,-1))==4):
			ret = {"code": "ORDER_OUT_OF_LIMIT","message": "每个用户只能下一单"}	
		#	print "access_token :",access_token
		#	print "user_name  message :",(conn.lrange("user_"+cartMsg[1],0,-1))
		#	print "下单 error", "  每个用户只能下一单"
			web.ctx.status = '403 Forbidden'
			return json.dumps(ret)

		if len(cartMsg) == 3 :#and len(conn.lrange("user_"+cartMsg[1],0,-1)) !=4:
			ret = {}
			ret["id"] = get_random_string()
			conn.rpush("user_"+cartMsg[1],"true")
			conn.rpush("order_"+access_token,{"id":int(ret["id"]),"items":[],"total":0})
			conn.rpush(order_list_key,ret["id"])
		#	print "下单ok  但是购物车为空"
			web.ctx.status = '200 OK'
			return json.dumps(ret);

		food_infos = []
		for i in range(3,len(cartMsg)):
			dicts = cartMsg[i].split('_')
			tmp = {"food_id":int(dicts[0]),"count":int(dicts[1])}
			food_infos.append(tmp)
		total_price = 0
		for i in range(len(food_infos)):
			item = food_infos[i]
			counts = 0-int(item["count"])
			if(conn.hincrby( "food_"+str(item["food_id"]),"stock",counts) < 0) or (len(conn.lrange("user_"+cartMsg[1],0,-1))==4) :
				conn.hincrby( "food_"+str(item["food_id"]),"stock",0-counts)
				for j in range(0,i):
					item = food_infos[j]
					conn.hincrby( "food_"+str(item["food_id"]),"stock",int(item["count"]))
				ret = {"code": "FOOD_OUT_OF_STOCK","message": "食物库存不足"}	
		#		print "下单 error", "  食物库存不足"
				web.ctx.status = '403 Forbidden'
				return json.dumps(ret)
			total_price = total_price +  int(item["count"])  * int(conn.hget("food_"+str(item["food_id"]),"price"))
		conn.rpush("user_"+cartMsg[1],"true")
		ret = {}
		ret["id"] = get_random_string()
		message = {}
		message["id"] = ret["id"] 
		message["items"] = food_infos
		message["total"] = int(total_price)
		conn.hset("order_"+access_token,"id",ret["id"])
		conn.hset("order_"+access_token,"items",food_infos)
		conn.hset("order_"+access_token,"total",total_price)
		conn.hset("order_"+access_token,"user_id",cartMsg[0])
		#conn.rpush("order_"+access_token,message,cartMsg[1])
		#d订单id list
		conn.rpush(order_list_key,"order_"+access_token)
		#print "total_price: ",total_price
		#print "message:" ,message
		#print "orders ok"
		web.ctx.status = '200 OK'
		return json.dumps(ret)

#查询订单详情
	def GET(self):
		access_token = ""
		#token 在参数parameter里
		if(access_token == ""):
			parameter123 = web.input()
			#print "parameter123:", parameter123
			access_token = str(parameter123.get("access_token",""))
		
		conn = redis.Redis(connection_pool = redisPool)
		#token 在header里
		if(access_token == ""):
			#print "parameter access_token is NULL"
			#print web.ctx.env
			access_token = web.ctx.env.get("HTTP_ACCESS_TOKEN","")
			#print "access_token 2: ",access_token
			if(access_token == "" or (not conn.exists(access_token))):
				#print "headers access_token is NULL"
		#		print "下单 error", "  token为空"
				ret = {"code": "INVALID_ACCESS_TOKEN","message": "无效的令牌"}	
				web.ctx.status = '401 Unauthorized'
				return json.dumps(ret)
		#print "access_token: ",access_token
		if(not conn.exists("order_"+access_token)):
			ret = {}	
			#print "下单 error", " 用户无下单 "
			return json.dumps(ret)

		
		#ret = conn.lrange("order_"+ access_token,0,-1)[0]
		ret = {}
		ret["id"] = conn.hget("order_"+ access_token,"id")
		ret["items"] = eval(conn.hget("order_"+ access_token,"items"))
		#print type(ret["items"])
		ret["total"] = int(conn.hget("order_"+ access_token,"total"))
		#print conn.lrange(access_token,0,-1)[1] +"  查询订单成功"
		retlist = [ret]
		return json.dumps(retlist)

class admin_orders:
	def GET(self):
		access_token = ""
		#token 在参数parameter里
		if(access_token == ""):
			parameter123 = web.input()
			#print "parameter123:", parameter123
			access_token = str(parameter123.get("access_token",""))
		
		conn = redis.Redis(connection_pool = redisPool)
		#token 在header里
		if(access_token == ""):
			#print "parameter access_token is NULL"
			#print web.ctx.env
			access_token = web.ctx.env.get("HTTP_ACCESS_TOKEN","")
			#print "access_token 2: ",access_token
			if(access_token == "" or (not conn.exists(access_token))):
				#print "headers access_token is NULL"
		#		print "下单 error", "  token为空"
				ret = {"code": "INVALID_ACCESS_TOKEN","message": "无效的令牌"}	
				web.ctx.status = '401 Unauthorized'
				return json.dumps(ret)
		user_info = conn.lrange(access_token,0,-1)
		if(str(user_info[1]) != "root"):
			ret = {"code": "INVALID_ACCESS_TOKEN","message": "非root用户不能查询该接口"}	
			web.ctx.status = '401 Unauthorized'
		#	print "非root用户不能查询该接口"
			return json.dumps(ret)

		order_key_list = conn.lrange(order_list_key,0,-1)
		respon = []
		for order_key in order_key_list:
			ret = {}
			ret["id"] = conn.hget(order_key,"id")
			ret["items"] = eval(conn.hget(order_key,"items"))
			ret["total"] = int(conn.hget(order_key,"total"))
			ret["user_id"] = int(conn.hget(order_key,"user_id"))
			respon.append(ret)
		#print "管理员查询订单成功"
		return json.dumps(respon)




if __name__ == "__main__":
	init_user_and_food_2_redis()
	#sys.argv[1] = str(app_port)
	app.run()
