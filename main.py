#import gtts
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
# from playsound import playsound
# from gtts import gTTS
# import speech_recognition as sr
#import os
import hashlib
from datetime import datetime
import nltk
from nltk.tokenize import sent_tokenize
import json
import random

#from playsound import playsound
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__, template_folder='anasayfa')
app.secret_key = 'your_secret_key'

# MySQL bağlantı bilgilerini ayarlayın
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'chatbot_project'

mysql = MySQL(app)


@app.route('/')
def open_html():
    return render_template('giris.html')


@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':

        username = request.form['exampleInputEmail1']
        password = request.form['exampleInputPassword1']

        # Veritabanı bağlantısını al
        cur = mysql.connection.cursor()

        # Veritabanında kullanıcıyı sorgula
        cur.execute("SELECT UserEmail, UserPassword, UserImage FROM users WHERE UserEmail = %s", (username,))
        user = cur.fetchone()

        if user:
            # Veritabanından alınan hashlenmiş şifre
            hashed_password_from_db = user[1]

            # Kullanıcının girdiği şifreyi MD5 olarak hashle
            hashed_password_input = hashlib.md5(password.encode()).hexdigest()

            if hashed_password_input == hashed_password_from_db:
                # Oturum açan kullanıcının adını session'a kaydet
                session['username'] = username

                # Giriş başarılı, istediğiniz sayfaya yönlendirin
                return redirect(url_for('deneme'))

    # Giriş başarısızsa hata mesajıyla birlikte ana sayfaya geri dön
    sesli_uyari = "Yanlış şifre girdiniz."
    # oku(sesli_uyari)
    return render_template('giris.html', error='Hatalı kullanıcı adı veya şifre.')


@app.route('/ekle_kullanici', methods=['POST'])
def ekle_kullanici():
    ad = request.form['ad']
    soyad = request.form['soyad']
    mail = request.form['mail']
    sifre = request.form['sifre']
    durum = request.form['durum']
    tarih = request.form['tarih']
    durum1 = request.form['durum1']

    # Şifreyi MD5 olarak hashle
    hashed_password = hashlib.md5(sifre.encode()).hexdigest()

    cur = mysql.connection.cursor()

    # Veritabanında aynı e-posta adresi olup olmadığını kontrol et
    cur.execute("SELECT UserEmail FROM users WHERE UserEmail = %s", (mail,))
    existing_email = cur.fetchone()

    if existing_email:
        # Eğer e-posta zaten varsa kullanıcıya bir uyarı göster
        sesli_uyari1 = "Girdiğiniz Mail adresi kayıtlı."
        # oku1(sesli_uyari1)
        return redirect(url_for('open_html'))
    else:
        # Eğer e-posta yoksa kullanıcıyı kaydet
        cur.execute(
            "INSERT INTO users (UserName, UserSurname, UserEmail, UserPassword, UserStatus, UserCreatedDate, UserImage) VALUES (%s ,%s, %s, %s, %s, %s, %s)",
            (ad, soyad, mail, hashed_password, durum, tarih, durum1,))
        mysql.connection.commit()

        cur.close()
        return redirect(url_for('open_html'))


@app.route('/deneme')
def deneme():
    # Kullanıcı adını session'dan al
    username = session.get('username')

    if username:
        # Veritabanından sohbet verilerini al
        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT ChatStatus, ChatTitle FROM chats WHERE UserEmail = %s AND ChatID IN (SELECT MIN(ChatID) FROM chats WHERE UserEmail = %s GROUP BY ChatNumber order by ChatNumber desc)",
            (username, username))
        chat_statuses_without_zero = cur.fetchall()

        cur.execute(
            "SELECT ChatStatus FROM chats WHERE (UserEmail, ChatNumber) IN (SELECT UserEmail, MAX(ChatNumber) FROM chats GROUP BY UserEmail) AND UserEmail = %s",
            (username,))
        chat_statuses_max_value = cur.fetchall()

        # Son eklenen ChatNumber'ı al
        cur.execute("SELECT MAX(ChatNumber) FROM chats WHERE UserEmail = %s", (username,))
        last_chat = cur.fetchone()

        if last_chat:
            last_chat_number = last_chat[0]  # Son eklenen ChatNumber'ı alıyoruz
        else:
            last_chat_number = 1

        cur.execute("SELECT ChatStatus, ChatTitle FROM chats WHERE UserEmail = %s AND ChatNumber =%s",
                    (username, last_chat_number))
        chat_statuses = cur.fetchall()

        # Kullanıcının resim bağlantısını al
        cur.execute("SELECT UserImage FROM users WHERE UserEmail = %s", (username,))
        user_image = cur.fetchone()[0]  # İlk sütunun değerini al

        cur.close()

        return render_template('deneme.html', username=username, chat_statuses=chat_statuses,
                               chat_statuses_without_zero=chat_statuses_without_zero, last_chat_number=last_chat_number,
                               user_image=user_image, chat_statuses_max_value=chat_statuses_max_value)

    else:
        return redirect(url_for('open_html'))


nltk.download('punkt')


@app.route('/get_chat_status', methods=['POST'])
def get_chat_status():
    username = session['username']

    if request.method == 'POST':
        chat_title = request.json.get('chat_title')

        # Bu noktada chat_title'ı kontrol etmek için bir print kullanabilirsiniz:
        print("Received chat_title:", chat_title)

        cur = mysql.connection.cursor()
        cur.execute("SELECT ChatStatus FROM chats WHERE UserEmail = %s AND ChatTitle = %s", (username, chat_title,))
        chat_statuses = cur.fetchall()
        cur.close()

        if chat_statuses:
            statuses = [status[0] for status in chat_statuses]
            return jsonify({'chat_statuses': statuses})
        else:
            return jsonify({'error': 'Chat status not found for the given ChatTitle'})

    return jsonify({'error': 'Invalid request'})


@app.route('/get_chat_number', methods=['POST'])
def get_chat_number():
    if request.method == 'POST':
        chat_title = request.json.get('chat_title')

        # Bu noktada chat_title'ı kontrol etmek için bir print kullanabilirsiniz:
        print("Received chat_title for ChatNumber:", chat_title)

        cur = mysql.connection.cursor()
        cur.execute("SELECT ChatNumber FROM chats WHERE ChatTitle = %s", (chat_title,))
        chat_number = cur.fetchone()
        cur.close()

        if chat_number:
            return jsonify({'chat_number': chat_number[0]})
        else:
            return jsonify({'error': 'Chat number not found for the given ChatTitle'})

    return jsonify({'error': 'Invalid request'})


@app.route('/ekle_kullanici2', methods=['POST'])
def ekle_kullanici2():
    sohbet = request.form['sohbet']
    number = request.form["chatnumber"]

    tarihbugun = datetime.now().strftime('%Y-%m-%d')
    username = None

    if 'username' in session:
        username = session['username']

    cumleler = sent_tokenize(sohbet)

    if cumleler:
        baslik = cumleler[0]
        baslik = baslik.split()[0] if baslik else None
    else:
        baslik = None

    cur1 = mysql.connection.cursor()

    # Veritabanında aynı UserEmail ve ChatNumber değerlerini içeren bir kayıt var mı kontrol ediyoruz
    cur1.execute("SELECT ChatTitle FROM chats WHERE UserEmail = %s AND ChatNumber = %s LIMIT 1", (username, number))
    existing_chat_title = cur1.fetchone()

    if existing_chat_title:
        # Eğer varsa, ilk girilen ChatTitle değerini bulduk
        baslik = existing_chat_title[0]

    if number is None or not str(number).isdigit():
        number = 1
    else:
        number = int(number)

    cur1.execute(
        "INSERT INTO chats (ChatCreatedDate, ChatStatus, ChatTitle, UserEmail, ChatNumber, ChatType) VALUES (%s, %s, %s, %s, %s, 1)",
        (tarihbugun, sohbet, baslik, username, number))

    mysql.connection.commit()

    # Örnek veri seti
    with open('veriler.json', 'r', encoding='utf-8') as dosya:
        veri_seti = json.load(dosya)

    # Veri setini tf-idf matrisine dönüştürme
    sorular = list(veri_seti.keys())
    cevaplar = [" ".join(veri_seti[soru]) for soru in sorular]

    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(cevaplar)

    # while True:
    # soru = input(sohbet)
    # if soru.lower() == 'q':
    # print("Çıkış yapılıyor...")
    # break

    # Kullanıcının girdiği soruyu tf-idf'ye dönüştürme
    soru_tfidf = tfidf_vectorizer.transform([sohbet])

    # Benzerlik hesaplama
    benzerlik_skoru = cosine_similarity(soru_tfidf, tfidf_matrix)

    # En benzer cevabı bulma
    en_benzer_indeks = benzerlik_skoru.argmax()
    en_benzer_soru = sorular[en_benzer_indeks]
    secilen_cevap = random.choice(veri_seti[en_benzer_soru])
    # print(secilen_cevap)

    tarihbugun_chat = tarihbugun
    sohbet_chat = secilen_cevap
    baslik_chat = baslik
    username_chat = username
    number_chat = number
    cur1.execute(
        "INSERT INTO chats (ChatCreatedDate, ChatStatus, ChatTitle, UserEmail, ChatNumber, ChatType) VALUES (%s, %s, %s, %s, %s, 0)",
        (tarihbugun_chat, sohbet_chat, baslik_chat, username_chat, number_chat))

    mysql.connection.commit()
    cur1.close()
    return redirect(url_for('deneme'))


@app.route('/logout')
def logout():
    # Oturumu sonlandır ve tüm bilgileri sil
    session.pop('username', None)
    return redirect(url_for('open_html'))


#def oku(string):
#   gtts = gTTS(text=string, lang="tr")


#file = "answer.mp3"
#if os.path.exists(file):
#    os.remove(file)  # Dosyayı sil
#gtts.save(file)
#playsound(file)


#def oku1(string1):
#    gtts = gTTS(text=string1, lang="tr")


#file1 = "answer1.mp3"
#if os.path.exists(file1):
#os.remove(file1)  # Dosyayı sil
#gtts.save(file1)
#playsound(file1)

if __name__ == '__main__':
    app.run(debug=True)
