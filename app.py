from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from flask import Flask, request, jsonify, redirect, Response
import json
from bson import json_util
from bson.objectid import ObjectId
import uuid
import time
from copy import deepcopy

# Connect to our local MongoDB
client = MongoClient('mongodb://localhost:27017/')

# Choose InfoSys database
db = client['DSMarkets']
users = db['Users']
products = db['Products']

# Initiate Flask App
app = Flask(__name__)

users_sessions = {}

cart = {"Items": [], "Total Cost": 0}
receipt = {}
rawItems = []
rawQty = []
globalEmail = ""


def create_session(username):
    user_uuid = str(uuid.uuid1())
    users_sessions[user_uuid] = (username, time.time())
    return user_uuid


def is_session_valid(user_uuid):
    return user_uuid in users_sessions


@app.route('/createUser', methods=['POST'])
def create_user():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)

    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "username" in data or not "password" in data or not "email" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    if users.find({"email": f"{data['email']}"}).count() == 0:
        users.insert(
            {"email": f"{data['email']}", "username": f"{data['username']}", "password": f"{data['password']}",
             "category": "regular"})
        return Response(data['email'] + " was added to the MongoDB", mimetype='application/json', status=200)
    else:
        return Response("A user with the given email already exists", mimetype='application/json', status=400)


@app.route('/login', methods=['POST'])
def login():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "email" in data or not "password" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    if users.find({"email": f"{data['email']}", "password": f"{data['password']}"}).count() == 1:
        global globalEmail
        user_uuid = create_session(data['email'])
        res = {"uuid": user_uuid, "email": data['email']}
        globalEmail = data['email']



        return Response(json.dumps(res), mimetype='application/json', status=200)

    else:
        return Response("Wrong email or password, please try again.", mimetype='application/json', status=400)


@app.route('/getProduct', methods=['GET'])
def get_product():
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')

    if "name" in data:
        uuid = request.headers.get('authorization')

        if is_session_valid(uuid):



            if (products.find({"name": f"{data['name']}"}).count()!=0):
                productscursor = products.find({"name": f"{data['name']}"}).sort("name")
                productsearch = json.loads(json_util.dumps(productscursor))

                return Response(json.dumps(productsearch), status=200, mimetype='application/json')
            else:
                return Response("Product(s) not found", status=400, mimetype="application/json")
        else:
            return Response("Not authorized", status=401, mimetype='application/json')
    elif "category" in data:
        uuid = request.headers.get('authorization')

        if is_session_valid(uuid):

            if (products.find({"category": f"{data['category']}"}).count()!=0):
                productscursor = products.find({"category": f"{data['category']}"}).sort("price")
                productsearch = json.loads(json_util.dumps(productscursor))

                return Response(json.dumps(productsearch), status=200, mimetype='application/json')
            else:
                return Response("Product(s) not found", status=400, mimetype="application/json")
        else:
            return Response("Not authorized", status=401, mimetype='application/json')
    elif "id" in data:
        uuid = request.headers.get('authorization')

        if is_session_valid(uuid):

            if products.find({"_id": ObjectId(data['id'])}).count()!=0:
                productscursor = products.find({"_id": ObjectId(data['id'])}).sort("price")
                productsearch = json.loads(json_util.dumps(productscursor))

                return Response(json.dumps(productsearch), status=200, mimetype='application/json')
            else:
                return Response("Product(s) not found", status=400, mimetype="application/json")
        else:
            return Response("Not authorized", status=401, mimetype='application/json')


@app.route('/addToCart', methods=['GET'])
def add_to_cart():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "id" in data or not "qty" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uuid = request.headers.get('authorization')

    if is_session_valid(uuid):
        productcursor = products.find_one({"_id": ObjectId(data['id'])})
        productsearch = json.loads(json_util.dumps(productcursor))
        qty = data['qty']
        if productsearch:

            cart['Total Cost'] = float(cart['Total Cost']) + float(productsearch['price']) * float(qty)
            cart['Items'].append(productsearch['name'] + " x" + qty)
            rawItems.append(productsearch['name'])
            rawQty.append(qty)

            return Response(json.dumps(cart), status=200, mimetype='application/json')
        else:
            return Response("Product not found", status=400, mimetype="application/json")
    else:
        return Response("Not authorized", status=401, mimetype='application/json')


@app.route('/showCart', methods=['GET'])
def show_cart():
    uuid = request.headers.get('authorization')

    if is_session_valid(uuid):
        if cart:
            return Response(json.dumps(cart), status=200, mimetype='application/json')
        else:
            return Response("Cart is empty.", status=400, mimetype="application/json")
    else:
        return Response("Not authorized", status=401, mimetype='application/json')


@app.route('/deleteFromCart', methods=['DELETE'])
def delete_items():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "id" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uuid = request.headers.get('authorization')
    if is_session_valid(uuid):
        delcursor = products.find_one({"_id": ObjectId(data['id'])})
        delsearch = json.loads(json_util.dumps(delcursor))

        delFound = False
        delIndex = 0
        if delsearch:
            for x in range(len(rawItems)):
                if delsearch['name'] == rawItems[x]:
                    delFound = True
                    delIndex = x

            if delFound:

                rawItems.pop(int(delIndex))
            
                cart['Items'].pop(x)
            
                cart['Total Cost'] = cart['Total Cost'] - float(delsearch['price'])*float(rawQty[x])
                rawQty.pop(int(delIndex))
                return Response(json.dumps(cart), status=200, mimetype='application/json')
            else:
                return Response("Product not in cart", status=400, mimetype='application/json')
        else:
            return Response("Product doesn't exist", status=400, mimetype='application/json')
    else:
        return Response("Not authorized", status=401, mimetype='application/json')


@app.route('/purchaseCart', methods=['PATCH'])
def purchase_cart():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "card" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uuid = request.headers.get('authorization')

    if is_session_valid(uuid):
        if len(data['card']) == 16:
            for y in range(len(rawItems)):
                purchaseCursor = products.find_one({"name": f"{rawItems[y]}"})
                purchaseSearch = json.loads(json_util.dumps(purchaseCursor))
                newQty = int(purchaseSearch['stock']) - int(rawQty[y])
                products.update_one(
                    {'name': rawItems[y]},
                    {'$set' : {'stock': newQty}}
                )
            rawQty.clear()
            rawItems.clear()
            
            users.update_one(
                {"email": f"{globalEmail}"},
                {"$push": {"orderHistory": f"{cart}"}}
            )
            receipt=deepcopy(cart)
            cart.clear()
            return Response(json.dumps(receipt), status=200, mimetype="application/json")

        else:
            return Response("Invalid card information", status=400, mimetype="application/json")

    else:
        return Response("Not authorized", status=401, mimetype='application/json')


@app.route('/showOrderHistory', methods=['GET'])
def show_order_history():
    ordercursor = users.find({"email": f"{globalEmail}"},{"_id":0,"email":0,"username":0,"password":0,"category":0})
    ordersearch = json.loads(json_util.dumps(ordercursor))
    uuid = request.headers.get('authorization')
    if is_session_valid(uuid):

        if ordersearch:
            return Response(json_util.dumps(ordersearch), status=200, mimetype='application/json')
        else:
            return Response("No orders found.", status=400, mimetype="application/json")
    else:
        return Response("Not authorized", status=401, mimetype='application/json')


@app.route('/deleteUser', methods=['DELETE'])
def delete_user():
    uuid = request.headers.get('authorization')
    if is_session_valid(uuid):
        global globalEmail
        users.delete_one({"email": f"{globalEmail}"})
        globalEmail= None
        rawQty.clear()
        rawItems.clear()
        cart.clear()
        return Response("User has been deleted", status=200, mimetype='application/json')
    else:
        return Response("Authentication failed", status=401, mimetype='application/json')

app.route("/insertProduct", methods=['PATCH'])
def insert_product():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "name" in data or not "price" in data or not "description" in data or not "category" in data or not "stock" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uuid = request.headers.get('authorization')
    if is_session_valid(uuid):
        userinfocursor = users.find_one({"email":f"{globalEmail}"})
        userinfosearch = json.loads(json_util.dumps(userinfocursor))

        if userinfosearch['category'] == "admin":
            products.insert_one(
                {
                    "name":f"{data['name']}",
                    "category":f"{data['category']}",
                    "stock":f"{data['stock']}",
                    "description":f"{data['description']}",
                    "price":f"{data['price']}"
                }
            )
            return Response("Product succesfully added.", status=200, mimetype='application/json')
        else:
            return Response("This action requires admin privileges.", status=400, mimetype="application/json")
    else:
        return Response("Authentication failed", status=401, mimetype='application/json')

app.route("/deleteProduct", methods=['DELETE'])
def delete_product():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "id" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uuid = request.headers.get('authorization')
    if is_session_valid(uuid):
        userinfocursor = users.find_one({"email": f"{globalEmail}"})
        userinfosearch = json.loads(json_util.dumps(userinfocursor))

        if userinfosearch['category'] == "admin":
            if products.find_one({"_id":ObjectId(data['id'])}):
                products.delete_one({"_id":ObjectId(data['id'])})
                return Response("Product succesfully deleted.", status=200, mimetype='application/json')
            else:
                return Response("Product not found.", status=400, mimetype='application/json')

        else:
            return Response("This action requires admin privileges.", status=400, mimetype="application/json")
    else:
        return Response("Authentication failed", status=401, mimetype='application/json')

@app.route("/modifyProduct", methods=['PATCH'])
def modify_product():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')

    if not "id" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    if not "name" in data and not "price" in data and not "description" in data and not "category" in data and not "stock" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uuid = request.headers.get('authorization')
    if is_session_valid(uuid):
        userinfocursor = users.find_one({"email":f"{globalEmail}"})
        userinfosearch = json.loads(json_util.dumps(userinfocursor))

        if userinfosearch['category'] == "admin":
                if "name" in data:

                    products.update_one(
                        {
                            "_id":ObjectId(data['id'])
                        },
                        {
                            {"$set":{"name": f"{data['name']}"}}
                        })
                if "price" in data:
                    products.update_one(
                        {
                            "_id": ObjectId(data['id'])
                        },
                        {
                            {"$set": {"price": f"{data['price']}"}}
                        })
                if "description" in data:
                    products.update_one(
                        {
                            "_id": ObjectId(data['id'])
                        },
                        {
                            {"$set": {"description": f"{data['description']}"}}
                        })
                if "stock" in data:
                    products.update_one(
                        {
                            "_id": ObjectId(data['id'])
                        },
                        {
                            {"$set": {"name": f"{data['stock']}"}}
                        })

                return Response("Product succesfully modified.", status=200, mimetype='application/json')
        else:
            return Response("This action requires admin privileges.", status=400, mimetype="application/json")
    else:
        return Response("Authentication failed", status=401, mimetype='application/json')



# Run Flask App
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
