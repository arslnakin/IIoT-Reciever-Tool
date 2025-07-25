import paho.mqtt.client as mqtt
import time

# Broker ayarları
broker_adresi = "localhost"  # Halka açık bir test broker'ı
port = 1883
konu = "ev/oturma_odasi/sicaklik"  # Mesajın gönderileceği konu (topic)

# Broker'a başarıyla bağlanıldığında çalışacak fonksiyon
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"{broker_adresi} adresine başarıyla bağlanıldı!")
    else:
        print(f"Bağlantı hatası! Kod: {rc}")

# İstemci (client) oluşturma
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "PythonPublisher") # Benzersiz bir client ID verin
client.on_connect = on_connect # Bağlantı durumunda on_connect fonksiyonunu çağır

# Broker'a bağlanma
client.connect(broker_adresi, port, 60)

# Mesaj göndermek için bir döngü
# Bu döngü, programın hemen kapanmasını engeller ve mesaj gönderimini sağlar.
client.loop_start()

try:
    sicaklik = 24.5
    while True:
        # Mesajı oluşturma ve gönderme
        mesaj = f"Sıcaklık: {sicaklik:.1f} C"
        result = client.publish(konu, mesaj)
        
        # Gönderim durumunu kontrol etme
        status = result[0]
        if status == 0:
            print(f"'{konu}' konusuna mesaj gönderildi: '{mesaj}'")
        else:
            print(f"'{konu}' konusuna mesaj gönderilemedi.")
            
        sicaklik += 0.1 # Sıcaklığı her seferinde biraz artır
        time.sleep(5) # 5 saniye bekle

except KeyboardInterrupt:
    print("Program sonlandırılıyor.")
    client.loop_stop()
    client.disconnect()