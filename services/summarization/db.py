import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

DR_JIB_CONVERSATIONS_COLLECTION = 'dr_jib_conversations'

cred = credentials.Certificate(r"./firebase_service_account.json")
test = firebase_admin.initialize_app(cred)

db = firestore.client()