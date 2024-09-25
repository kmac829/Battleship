from flask import Flask, request, render_template 
from flask_sqlalchemy import SQLAlchemy
from random import randint
import _json

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.sqlite"
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)

class Move(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, nullable=False)
    row = db.Column(db.Integer, nullable=False)
    column = db.Column(db.Integer, nullable=False)
    is_hit = db.Column(db.Integer, default=0)
    is_player = db.Column(db.Integer, default=0)

class Ship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, nullable=False)
    is_player = db.Column(db.Integer, default=0)
    size = db.Column(db.Integer, default=0)
    placement = db.Column(db.String)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    winner = db.Column(db.Integer, default=-1)

with app.app_context():
    db.create_all()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/startgame", methods=["POST"])
def start_game():
    user_id = request.json["user_id"]
    game = Game(user_id=user_id)
    db.session.add(game)
    db.session.commit()
    ships = [5, 4, 3, 3, 2]
    placements = []
    for ship in ships:
        direction = randint(0,1)
        x = 9
        y = 9
        if direction:
            y -= ship
        else:
            x -= ship

        found = True
        while found:
            start = [randint(0,x), randint(0,y)]
            placement = []
            found = False
            for i in range(ship):
                # detect double placement
                
                for test in placements:
                    for position in test:
                        if position[0] == start[0] and position[1] == start [1]:
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

                placement.append(start[0:])
                if direction:
                    start[1] += 1
                else:
                    start[0] += 1
            if not found:   
                placements.append(placement)
    for placement in placements:
        ship = Ship(is_player = False, game_id = game.id, size = len(placement), placement = "|".join(",".join([str(y) for y in x]) for x in placement))
        db.session.add(ship)
        db.session.commit()
    # create AI Placements
    return {
        "id": game.id,
        "user_id": game.user_id,
        "winner": game.winner
    }

@app.route("/api/shipplacement", methods=["POST"])
def ship_placement():
    game_id= request.json["game_id"]
    size= request.json["size"]
    placement= request.json["placement"]
    ship = Ship(game_id=game_id, is_player = True, size=size, placement=placement)
    db.session.add(ship)
    db.session.commit()
    return {
        "id": ship.id,
        "game_id":ship.game_id,
        "size": ship.size,
        "placement": ship.placement,
        "is_player": ship.is_player
    }

@app.route("/api/makemove", methods=["POST"])
def make_move():
    # Receive the move from the player
    row = request.json["row"]
    column = request.json["column"]
    game_id= request.json["game_id"]

    # Check if it hits AI ship
    ai_ships = db.session.execute(db.select(Ship).filter_by(game_id=game_id, is_player=False)).scalars()
    is_hit = False
    for ai_ship in ai_ships:
        placements = ai_ship.placement.split("|")
        for placement in placements:
            if placement == f"{row},{column}":
                is_hit = True
                break
        if is_hit:
            break
    
    player_move = Move(game_id=game_id, row=row, column=column, is_player=True, is_hit=is_hit)
    db.session.add(player_move)
    db.session.commit()

    # Check if player wins
    player_hits = db.session.execute(db.select(Move).filter_by(game_id=game_id, is_player=True, is_hit=True)).scalars()
    player_won = len(player_hits.all()) == 17
    if player_won:
        return {
            "player":{
                "id":player_move.id,
                "game_id": player_move.game_id,
                "row": player_move.row,
                "column": player_move.column,
                "is_hit": player_move.is_hit,
                "is_player": player_move.is_player
            },
            "ai":{
                "id":-1,
                "game_id": player_move.game_id,
                "row": -1,
                "column": -1,
                "is_hit": False,
                "is_player": False
            },
            "has_player_won": True,
            "has_ai_won": False
        }
    # Make AI Move
    ai_moves = db.session.execute(db.select(Move).filter_by(game_id=game_id, is_player=False)).scalars()
    move_found = True
    ai_row = -1
    ai_column = -1
    while move_found:
        move_found = False
        ai_row = randint(0,9)
        ai_column = randint(0,9)
        for move in ai_moves:
            if move.row == ai_row and move.column == ai_column:
                move_found = True
                break

    # Check if AI Hits
    player_ships = db.session.execute(db.select(Ship).filter_by(game_id=game_id, is_player=True)).scalars()
    is_hit = False
    for player_ship in player_ships:
        placements = player_ship.placement.split("|")
        for placement in placements:
            if placement == f"{ai_row},{ai_column}":
                is_hit = True
                break
        if is_hit:
            print(player_ship.placement, ai_row, ai_column)
            break
    
    ai_move = Move(game_id=game_id, row=ai_row, column=ai_column, is_player=False, is_hit=is_hit)
    db.session.add(ai_move)
    db.session.commit()

    # Check if AI wins
    ai_hits = db.session.execute(db.select(Move).filter_by(game_id=game_id, is_player=False, is_hit=True)).scalars()
    ai_won = len(ai_hits.all()) == 17

    return {
        "player":{
            "id":player_move.id,
            "game_id": player_move.game_id,
            "row": player_move.row,
            "column": player_move.column,
            "is_hit": player_move.is_hit,
            "is_player": player_move.is_player
        },
        "ai":{
            "id":ai_move.id,
            "game_id": ai_move.game_id,
            "row": ai_move.row,
            "column": ai_move.column,
            "is_hit": ai_move.is_hit,
            "is_player": ai_move.is_player
        },
        "has_player_won": False,
        "has_ai_won": ai_won
    }


@app.route("/api/login", methods=["POST"])
def login():
    username = request.json["username"]
    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one()
    return {
        "id":user.id,
        "username":user.username
    } 

@app.route("/api/createuser", methods=["POST"])
def create_user():
    username = request.json["username"]
    user = User(username=username)
    db.session.add(user)
    db.session.commit()
    return {
        "id":user.id,
        "username":user.username
    } 