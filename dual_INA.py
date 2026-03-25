from machine import Pin, SoftI2C
import ssd1306
import time
import neopixel

# Configuração dos Botões (Mantido conforme original)
btn_sw = Pin(22, Pin.IN, Pin.PULL_UP)

# Configuração da Matriz de LEDs
NUM_LEDS = 25
np = neopixel.NeoPixel(Pin(7), NUM_LEDS)
matriz_ligada = False
ultimo_estado_sw = 1
POTENCIA_MAX_BRILHO = 50.0 

# Endereço fixo solicitado
INA226_ADDR = 0x44  

# I2C1 (INA 1 e OLED) e I2C0 (INA 2)
i2c1 = SoftI2C(scl=Pin(3), sda=Pin(2)) # Barramento 1
i2c0 = SoftI2C(scl=Pin(1), sda=Pin(0)) # Barramento 0

oled = ssd1306.SSD1306_I2C(128, 64, i2c1)

# Funções de leitura adaptadas para receber o barramento como argumento
def ler_tensao_bus(i2c_bus):
    try:
        data = i2c_bus.readfrom_mem(INA226_ADDR, 0x02, 2)
        return ((data[0] << 8) | data[1]) * 1.25 / 1000
    except: return None

def ler_tensao_shunt(i2c_bus):
    try:
        data = i2c_bus.readfrom_mem(INA226_ADDR, 0x01, 2)
        raw = (data[0] << 8) | data[1]
        if raw > 32767: raw -= 65536
        return raw * 2.5 / 1_000_000
    except: return None

# Configuração de filtragem original (0x4727) aplicada a ambos os sensores
# Mantém a média de 16 amostras conforme seu código original
try:
    i2c1.writeto_mem(INA226_ADDR, 0x00, bytearray([0x47, 0x27]))
    i2c0.writeto_mem(INA226_ADDR, 0x00, bytearray([0x47, 0x27]))
except:
    print("Erro ao configurar INAs")

while True:
    # Leitura Sensor 1 (I2C0)
    v1 = ler_tensao_bus(i2c0)
    s1 = ler_tensao_shunt(i2c0)
    i1 = (s1 / 0.1) * 1000 if s1 is not None else 0
    p1 = v1 * i1 if v1 and i1 else 0

    # Leitura Sensor 2 (I2C1)
    v2 = ler_tensao_bus(i2c1)
    s2 = ler_tensao_shunt(i2c1)
    i2 = (s2 / 0.1) * 1000 if s2 is not None else 0
    p2 = v2 * i2 if v2 and i2 else 0
    
    # Cálculo da Eficiência (Potência 2 / Potência 1)
    eficiencia = (p2 / p1) * 100 if p1 > 0 else 0

    # --- Lógica de Toggle da Matriz (Botão do Joystick) ---
    estado_sw = btn_sw.value()
    if estado_sw == 0 and ultimo_estado_sw == 1:
        matriz_ligada = not matriz_ligada
        time.sleep(0.05)
    ultimo_estado_sw = estado_sw

    # Brilho baseado na potência do Sensor 1 (Painel)
    if matriz_ligada and p1 > 0:
        fator = min(p1 / POTENCIA_MAX_BRILHO, 1.0)
        brilho = int(255 * fator)
        for i in range(NUM_LEDS): np[i] = (brilho, brilho, brilho)
        np.write()
    else:
        for i in range(NUM_LEDS): np[i] = (0, 0, 0)
        np.write()

    # --- Interface OLED Organizda em Colunas ---
    oled.fill(0)
    oled.text(" Motor | Gerador", 0, 0)
    oled.text("-" * 16, 0, 7)
    
    # Tensões na mesma linha
    oled.text("V:{:>5.2f}|{:>5.2f}  V".format(v1 if v1 else 0, v2 if v2 else 0), 0, 18)
    
    # Correntes na linha de baixo (mA)
    oled.text("I:{:>5.1f}|{:>5.1f} mA".format(i1, i2), 0, 30)
    
    # Potências na terceira linha (mW)
    oled.text("P:{:>5.0f}|{:>5.0f} mW".format(p1, p2), 0, 42)
    
    # Eficiência embaixo de tudo
    oled.text("Eficien: {:.1f} %".format(eficiencia), 0, 56)
    
    oled.show()
    time.sleep(0.5)