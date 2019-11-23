from flask import Flask, render_template, flash, request, redirect
import ssl
from peewee import *
from playhouse.db_url import connect
import pymysql
import datetime
import requests
import json
import os

DB_URL = 'mysql+pool://deal:deal1234@deal.ct7ygagy10fd.ap-northeast-2.rds.amazonaws.com:3306/deal'

db = connect(DB_URL)
kakao_admin_key = ""
kko_pay_json = open(os.getcwd()+'/kakao_key.json')
key_data=json.load(kko_pay_json)
kakao_admin_key=key_data['kakao_auth']


class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    email = CharField(primary_key=True)
    password = CharField()
    level = IntegerField(default=0)
    state = IntegerField(default=1)
    role = IntegerField(default=1)
    register_type = IntegerField(default=0)
    agree_with_terms = BooleanField(default=False)
    is_phone_authentication = IntegerField()
    is_account_authentication = IntegerField()
    profile_photo_url = IntegerField()
    last_login_datetime = DateTimeField(default=datetime.datetime.now())
    created_at = DateTimeField(default=datetime.datetime.now())

    class Meta:
        db_table = 'user'

class DepositPoint(BaseModel):
    id = IntegerField(primary_key=True)
    user_email = ForeignKeyField(User, column_name='user_email')
    val = IntegerField()
    kind = IntegerField()
    created_at = DateTimeField()

    class Meta:
        db_table = 'deposit_point'

class KakaoPayModel(BaseModel):
    id = IntegerField(primary_key=True)
    user_email = ForeignKeyField(User, column_name='user_email')
    tid = CharField()
    state = IntegerField()
    val = IntegerField()
    created_at = DateTimeField()

    class Meta:
        db_table = 'kakaopay'

#######################################################

app = Flask(__name__)

@app.route('/success', methods=['GET'])
def success():
    pg_token = request.args.get('pg_token')
    print(pg_token)

    pay_info = KakaoPayModel.select(KakaoPayModel.user_email, KakaoPayModel.tid)\
            .order_by((KakaoPayModel.created_at).desc())\
            .limit(5).dicts()
    
    for row in pay_info:
        header = {
                'Authorization': kakao_admin_key
                }
        params = {
                'cid':'TC0ONETIME',
                'tid':str(row['tid']),
                'partner_order_id':'partner_order_id',
                'partner_user_id':str(row['user_email']),
                'pg_token':str(pg_token),
                }
        res = requests.post('https://kapi.kakao.com/v1/payment/approve', headers=header, data=params)
        if res.status_code != 200:
            continue
        
        res=res.json()
        user_email=res['partner_user_id']
        amount = res['amount']

        KakaoPayModel.update(state=1,tid="",val=0,created_at=datetime.datetime.now()).where(KakaoPayModel.user_email == user_email).execute()

        with db.atomic() as transaction:
            try:
                DepositPoint.create(
                    user_email=user_email,
                    val=amount['total'],
                    kind=2,
                    created_at=datetime.datetime.now(),
                )
            except Exception as e:
                print("EXCEPTION: "+str(e))

    return render_template('success.html')


if __name__ == '__main__':
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    ssl_context.load_cert_chain(certfile='future.crt', keyfile='future.key', password='secret')
    app.run(
        host='0.0.0.0',
        port=5555,
        debug= True,
        ssl_context = ssl_context,
    )

