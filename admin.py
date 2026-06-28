import psycopg2
import streamlit as st
from admin_brisi import prikazi_brisanje
from admin_unos import prikazi_unos
from admin_uredi import prikazi_uredivanje

# --- KONEKCIJA NA INTERNET BAZU (SUPABASE) ---
conn = psycopg2.connect(
    host=st.secrets["baza"]["host"],
    port=st.secrets["baza"]["port"],
    database=st.secrets["baza"]["database"],
    user=st.secrets["baza"]["user"],
    password=st.secrets["baza"]["password"],
    sslmode=st.secrets["baza"]["sslmode"],
    options="-c statement_timeout=5000"  # Parametar protiv smrzavanja ekrana
)
cursor = conn.cursor()

# Osiguravamo tablice i polja u bazi podataka na internetu
try:
    cursor.execute("ALTER TABLE cestice ADD COLUMN IF NOT EXISTS katastarska_opcina TEXT;")
    conn.commit()
except Exception:
    if conn: conn.rollback()


# --- JEDNOSTAVNA ZAŠTITA ZA ULAZ U APLIKACIJU ---# --- JEDNOSTAVNA ZAŠTITA ZA ULAZ IN ADMIN PANEL ---
if "admin_autentificiran" not in st.session_state:
    st.session_state["admin_autentificiran"] = False

if not st.session_state["admin_autentificiran"]:
    st.subheader("🔐 Kontrolna Ploca - Administracija")
    st.write("Unesite administratorske podatke za upravljanje arhivom:")
    
    u_admin_korisnik = st.text_input("Admin Korisnicko ime:", key="admin_user_input")
    u_admin_lozinka = st.text_input("Admin Lozinka:", type="password", key="admin_pass_input")
    
    if st.button("Prijavi se u sustav"):
        # Provjera odgovaraju li uneseni podaci sekciji [admin_credentials]
        if u_admin_korisnik == st.secrets["admin_credentials"]["username"] and u_admin_lozinka == st.secrets["admin_credentials"]["password"]:
            st.session_state["admin_autentificiran"] = True
            st.success("Uspjesna prijava u admin panel!")
            st.rerun()
        else:
            st.error("❌ Nevazece administratorsko korisnicko ime ili lozinka.")
            
    # Zaustavljamo izvrsavanje ako lozinka nije tocna
    st.stop()




st.set_page_config(page_title="Katastar - Administracija", layout="wide")
st.title("🔐 Kontrolna Ploča (Upravljanje Podacima)")



import psycopg2
import streamlit as st
conn = psycopg2.connect(
    host=st.secrets["baza"]["host"],
    port=st.secrets["baza"]["port"],
    database=st.secrets["baza"]["database"],
    user=st.secrets["baza"]["user"],
    password=st.secrets["baza"]["password"],
    sslmode=st.secrets["baza"]["sslmode"]
)
cursor = conn.cursor()



# Osiguravamo da tablice imaju potrebna polja na internetu
try:
    cursor.execute("ALTER TABLE povijest_dokumenata ADD COLUMN IF NOT EXISTS datoteka TEXT;")
    conn.commit()
except:
    if conn: conn.rollback()

try:
    cursor.execute("ALTER TABLE cestice ADD COLUMN IF NOT EXISTS katastarska_opcina TEXT;")
    conn.commit()
except:
    if conn: conn.rollback()

try:
    cursor.execute("ALTER TABLE cestice ADD COLUMN IF NOT EXISTS sifra TEXT;")
    conn.commit()
except:
    if conn: conn.rollback()


# Dohvat podrucja
cursor.execute("SELECT id, naziv_podrucja FROM podrucja")
sva_p = cursor.fetchall()
p_dict = {naziv: id for id, naziv in sva_p}
p_obrnuti_dict = {id: naziv for id, naziv in sva_p}

# Dohvat cestica
cursor.execute("SELECT id, broj_cestice FROM cestice")
c_glavni_dict = {broj: id for id, broj in cursor.fetchall()}

# Bocni dio za unos novog podrucja
st.sidebar.subheader("📍 Podrucja")
with st.sidebar.form("f_p", clear_on_submit=True):
    novo_p = st.text_input("Naziv novog podrucja:")
    if st.form_submit_button("Spremi Podrucje") and novo_p:
        try:
            cursor.execute("INSERT INTO podrucja (naziv_podrucja) VALUES (%s)", (novo_p,))
            conn.commit()
            st.success("Dodano!")
            st.rerun()
        except Exception as e:
            if conn: conn.rollback()
            st.error(f"Greska ili podrucje vec postoji!")

# Glavni tabovi na ekranu
tab_glavni1, tab_glavni2, tab_glavni3 = st.tabs([
    "➕ Unos Podataka", 
    "✍️ Uredi Cesticu", 
    "❌ Brisanje Podataka"
])

with tab_glavni1:
    prikazi_unos(conn, cursor, sva_p, p_dict)

with tab_glavni2:
    prikazi_uredivanje(conn, cursor, c_glavni_dict, p_dict, p_obrnuti_dict)

with tab_glavni3:
    prikazi_brisanje(conn, cursor, c_glavni_dict)

conn.close()



