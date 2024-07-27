from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = '1234'

def get_database_connection():
    conn = sqlite3.connect('fridge.db')
    return conn

def handle_initial_message():
    resp = MessagingResponse()
    resp.message("Hey !\nWelcome back to your Smart Fridge. What do you want to do -\n1 - Check items.\n2 - Get recipe ingredients.\n3 - List all the items.\n4 - Random Recipe.")
    session['conversation_state'] = 'started'
    return str(resp)

def handle_message(incoming_msg, conn):
    resp = MessagingResponse()
    cursor = conn.cursor()
    conversation_state = session.get('conversation_state')
    if conversation_state == 'started':
        if '1' in incoming_msg:
            resp.message("Enter the name of the item:")
            session['conversation_state'] = 'get_item_name'
        elif '2' in incoming_msg:
            resp.message("Enter the name of the recipe:")
            session['conversation_state'] = 'get_recipe_name'
        elif '3' in incoming_msg:
            cursor.execute("SELECT * FROM items;")
            rows = cursor.fetchall()
            items_list = "\n".join([f"{row[0]} - Quantity: {row[2]}, Expiry: {row[1]} days" for row in rows])
            resp.message("Here are all the items in your fridge:\n" + items_list)
            session.pop('conversation_state', None)
            return str(resp)
        elif '4' in incoming_msg:
            url = "https://www.themealdb.com/api/json/v1/1/random.php"
            response = requests.get(url)
            data = response.json()
            random_meal = data['meals'][0]
            meal_name = random_meal['strMeal']
            category = random_meal['strCategory']
            instructions = random_meal['strInstructions']
            meal_info = f"Random Meal: {meal_name}\nCategory: {category}\nInstructions: {instructions}"
            resp.message(meal_info)
            session.pop('conversation_state', None)
            return str(resp)
        else:
            resp.message("Sorry, I didn't understand your message.")
    elif conversation_state == 'get_item_name':
        session['item_name'] = incoming_msg
        cursor.execute("SELECT * FROM items WHERE name = ?;", (incoming_msg,))
        rows = cursor.fetchall()
        if rows:
            resp.message(f"You have {rows[0][2]} of {rows[0][0]} that will be expiring in {rows[0][1]} days.")
        else:
            resp.message("No item found with that name.")
        session.pop('conversation_state', None)
    elif conversation_state == 'get_recipe_name':
        session['recipe_name'] = incoming_msg
        url = "https://www.themealdb.com/api/json/v1/1/search.php?s=" + session['recipe_name']
        response = requests.get(url)
        ingredients_list = []
        if response.status_code == 200:
            data = response.json()
            if data['meals'] is not None:
                for meal in data['meals']:
                    for i in range(1, 21):
                        ingredient = meal.get(f'strIngredient{i}')
                        if ingredient:
                            measure = meal.get(f'strMeasure{i}')
                            ingredients_list.append((measure, ingredient))
        ingredients_message = ""
        for measure, ingredient in ingredients_list:
            ingredients_message += f"{measure} {ingredient}\n"
        message = str(ingredients_message)
        resp.message(message)
        session.pop('conversation_state', None)
    else:
        resp.message("Sorry, I didn't understand your message.")
    cursor.close()
    return str(resp)

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').lower()
    conn = get_database_connection()
    if 'hey' in incoming_msg:
        return handle_initial_message()
    else:
        response = handle_message(incoming_msg, conn)
        conn.close()
        return response

if __name__ == '__main__':
    app.run(debug=True, port=8080)
