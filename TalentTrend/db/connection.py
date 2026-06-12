from pymongo import MongoClient # pyright: ignore[reportMissingImports]

def get_db():
    client = MongoClient('mongodb+srv://varshasinbox1_db_user:Varsha%401700@cluster0.9f396vf.mongodb.net/')
    db = client['TalentTrend']
    print("Connected to MongoDB")
    return db

get_db()