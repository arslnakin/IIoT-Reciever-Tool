# IIoT Alıcı Aracı (IIoT Receiver Tool)

Bu proje, Endüstriyel Nesnelerin İnterneti (IIoT) alanında sıkça kullanılan iletişim protokollerini (OPC UA, Modbus, MQTT) test etmek, izlemek ve veri alışverişi yapmak için geliştirilmiş, PyQt6 tabanlı bir masaüstü uygulamasıdır.


*(Buraya uygulamanın bir ekran görüntüsü eklenebilir)*

## ✨ Temel Özellikler

Uygulama, sekmeli bir arayüz üzerinden dört ana modül sunar:

-   **🌐 Ağ Tarayıcı (Network Scanner):**
    -   Belirtilen bir IP aralığındaki (`192.168.1.0/24` gibi) aktif cihazları tespit eder.
    -   Cihazların canlı olup olmadığını `ping` ile kontrol ederek tarama süresini optimize eder.
    -   Yaygın IIoT portlarının (Modbus: 502, OPC UA: 4840, MQTT: 1883 vb.) açık olup olmadığını tarar.
    -   Bulunan açık portları ve potansiyel servisleri bir tabloda listeler.

-   **📈 OPC UA İstemcisi:**
    -   Bir OPC UA sunucusuna bağlanır.
    -   Sunucunun adres alanını (node'lar) bir ağaç yapısında gezinmenizi sağlar.
    -   Bir node'a tıklandığında anlık değerini okur.
    -   Bir node'a **çift tıklandığında** o node'un değer değişikliklerine abone olur ve gelen veriyi **gerçek zamanlı bir grafikte** çizer.
    -   Seçili node'a yeni bir değer yazma imkanı sunar.

-   **🔩 Modbus İstemcisi:**
    -   **Modbus TCP** ve **Modbus RTU** (seri port) protokollerini destekler.
    -   Belirtilen aralıklarla (polling) bir cihazdan veri okur.
    -   Okunan register/coil değerlerini adresleriyle birlikte bir tabloda gösterir (Decimal, Hex, Binary).

-   **📨 MQTT İstemcisi:**
    -   Bir MQTT Broker'ına bağlanır.
    -   Belirtilen bir konuya (topic) abone olarak gelen mesajları dinler.
    -   Gelen mesajları zaman damgası, konu ve içerik (payload) olarak bir tabloda listeler.
    -   İstenilen bir konuya mesaj yayınlama (publish) imkanı sunar.

-   **💾 Yapılandırma Yönetimi:**
    -   Tüm sekmelerdeki bağlantı ayarlarını tek bir JSON dosyasına kaydedebilir ve daha sonra geri yükleyebilirsiniz.

## 🚀 Kurulum ve Başlatma

1.  **Depoyu Klonlayın:**
    ```bash
    git clone https://github.com/your-username/IIoT-Reciever-Tool.git
    cd IIoT-Reciever-Tool
    ```

2.  **Sanal Ortam Oluşturun ve Aktif Edin:**
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # Linux / macOS
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Gerekli Kütüphaneleri Yükleyin:**
    *(Projede bir `requirements.txt` dosyası varsa, `pip install -r requirements.txt` komutunu kullanın. Yoksa, aşağıdaki kütüphaneleri manuel olarak yükleyin.)*
    ```bash
    pip install PyQt6 pyqtgraph asyncua pymodbus paho-mqtt
    ```

4.  **Uygulamayı Çalıştırın:**
    ```bash
    python main.py
    ```

## 🛠️ Test Sunucularını Kullanma

Uygulamanın özelliklerini test etmek için proje içinde hazır test sunucuları bulunmaktadır. Her bir sunucuyu ayrı bir terminalde çalıştırarak uygulamanın ilgili sekmesinden bağlantı kurabilirsiniz.

-   **OPC UA Test Sunucusu:**
    ```bash
    python tests/opcua_test_server.py
    ```
    Bu sunucu `opc.tcp://127.0.0.1:4840` adresinde çalışır ve 2 saniyede bir güncellenen `Temperature`, `Counter` ve `Status` adında üç değişken yayınlar.

-   **Modbus Test Sunucusu:**
    ```bash
    python tests/modbus_test_server.py
    ```
    Bu sunucu `127.0.0.4:502` adresinde bir Modbus TCP sunucusu başlatır ve belirli aralıklarla register ve coil değerlerini günceller.

-   **MQTT Test Sunucusu (Publisher):**
    ```bash
    python tests/mqtt_live_server.py
    ```
    Bu sunucu, yerel makinede çalışan bir MQTT broker'ına (`localhost:1883`) 5 saniyede bir `ev/oturma_odasi/sicaklik` konusuna mesaj yayınlar. Test için Mosquitto gibi bir MQTT broker'ını yerel makinenize kurmanız gerekebilir.

## ⚙️ Yapılandırma (Konfigürasyon)

Tüm sekmelerdeki IP adresi, port, konu gibi ayarları kalıcı hale getirmek için:

1.  Menüden `Dosya > Ayarları Kaydet` seçeneğine tıklayın.
2.  Ayarlarınızı bir `.json` dosyası olarak kaydedin.
3.  Daha sonra bu ayarları geri yüklemek için `Dosya > Ayarları Yükle` seçeneğini kullanın.

---

## 🤝 Katkıda Bulunma

Katkılarınız için teşekkürler! Lütfen pull request göndermekten veya issue açmaktan çekinmeyin.