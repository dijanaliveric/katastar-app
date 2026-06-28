import os
import psycopg2
import streamlit as st
from PIL import Image
import urllib.parse
import base64 
import warnings

conn = psycopg2.connect(
    host=st.secrets["baza"]["host"],
    port=st.secrets["baza"]["port"],
    database=st.secrets["baza"]["database"],
    user=st.secrets["baza"]["user"],
    password=st.secrets["baza"]["password"],
    sslmode=st.secrets["baza"]["sslmode"]
)
cursor = conn.cursor()


# OVO GASI DOSADNA PANDAS UPOZORENJA U TERMINALU
warnings.filterwarnings("ignore", category=UserWarning)

# --- JEDNOSTAVNA ZAŠTITA ZA ULAZ U APLIKACIJU ---
if "autentificiran" not in st.session_state:
    st.session_state["autentificiran"] = False

if not st.session_state["autentificiran"]:
    st.subheader("🔐 Privatna Obiteljska Arhiva")
    st.write("Unesite podatke za pristup koje ste dobili od administratora:")
    
    u_korisnik = st.text_input("Korisnicko ime:")
    u_lozinka = st.text_input("Lozinka:", type="password")
    
    if st.button("Pristupi arhivi"):
        # Provjera odgovaraju li uneseni podaci onima iz secrets.toml
        if u_korisnik == st.secrets["credentials"]["username"] and u_lozinka == st.secrets["credentials"]["password"]:
            st.session_state["autentificiran"] = True
            st.success("Uspjesna prijava!")
            st.rerun()
        else:
            st.error("❌ Nevazece korisnicko ime ili lozinka. Pokusajte ponovno.")
            
    st.stop()





datoteka = None

if "uploader_kljuc" not in st.session_state:
    st.session_state["uploader_kljuc"] = 0

upload_mapa = "dokumenti/rodbina_upload"
if not os.path.exists(upload_mapa):
    os.makedirs(upload_mapa)

# --- NOVI SQL BASE64 UPLOADER ZA RODBINU ---
datoteka_uploader = st.file_uploader(
    "Učitaj novi obiteljski dokument:",
    type=["png", "jpg", "jpeg", "pdf", "xlsx", "docx"],
    key=f"glavni_gornji_uploader_{st.session_state['uploader_kljuc']}",
)

if datoteka_uploader is not None:
    ekstenzija = datoteka_uploader.name.split(".")[-1].lower()
    if ekstenzija not in ["png", "jpg", "jpeg", "pdf", "xlsx", "docx"]:
        st.error("❌ Greška: Ovaj format datoteke nije dozvoljen!")
    else:
        try:
            # 1. Čitamo datoteku s mobitela/računala i pretvaramo je u tekst
            bajtovi = datoteka_uploader.read()
            tekstualni_b64 = base64.b64encode(bajtovi).decode('utf-8')
            kodirani_zapis = f"{datoteka_uploader.name}|||{tekstualni_b64}"
            
            # 2. Upisujemo dokument izravno u online bazu vezan uz ID 999999
            cursor.execute(
                """
                INSERT INTO povijest_dokumenata 
                (id_cestice, vrsta_lista, broj_lista_korisnika, starost_godina, upisani_vlasnik_posjednik, povijesna_napomena, datoteka) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    999999,                    # Vežemo uz našu opću česticu
                    "Poslani dokument",        # Kategorija dokumenta
                    "Online",                  # Izvor unosa
                    "2026",                    # Trenutna godina unosa
                    "Rodbina (Web)",           # Tko je unio
                    "Dokument poslan izravno s mobitela/računala.",
                    kodirani_zapis             # Cijela datoteka u obliku teksta
                ),
            )
            conn.commit()
            
            st.success(f"✅ Uspješno spremljeno u bazu podataka: {datoteka_uploader.name}")
            st.session_state["uploader_kljuc"] += 1
            st.rerun()
        except Exception as e:
            if conn: conn.rollback()
            st.error(f"❌ Došlo je do greške prilikom spremanja u bazu: {e}")

st.write("---")

# --- OSNOVNE POSTAVKE ---
st.set_page_config(page_title="Katastar Arhiva - Pregled", layout="wide")
st.title("🗺️ Obiteljska Arhiva Zemljišta i Čestica")



# --- 4. FIKSNI GUMBI ZA OPĆE DOKUMENTE I MATIČNE KNJIGE IZ BAZE (UNIVERZALNI MIME) ---
col_ikona1, col_ikona2, col_ikona3, _ = st.columns(4)

# Pomoćna funkcija za automatsko određivanje ispravnog MIME tipa datoteke
def dohvati_mime_tip(ime_datoteke):
    ime_nisko = ime_datoteke.lower()
    if ime_nisko.endswith('.pdf'): return "application/pdf"
    elif ime_nisko.endswith(('.jpg', '.jpeg')): return "image/jpeg"
    elif ime_nisko.endswith('.png'): return "image/png"
    elif ime_nisko.endswith('.xlsx'): return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif ime_nisko.endswith('.docx'): return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"

with col_ikona1:
    with st.popover("📋 Posjedovni Listovi"):
        st.markdown("### 📄 Opći katastarski dokumenti")
        st.write("Preuzmite posjedovne listove:")
        
        cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE id_cestice = 888888")
        svi_opci = cursor.fetchall()
        
        if svi_opci:
            for (sadrzaj,) in svi_opci:
                if sadrzaj and "|||" in sadrzaj:
                    d_ime, b64_kod = sadrzaj.split("|||", 1)
                    f_bajtovi = base64.b64decode(b64_kod)
                    st.download_button(
                        label=f"📥 {d_ime}",
                        data=f_bajtovi,
                        file_name=d_ime,
                        mime=dsub_mime if (dsub_mime := dohvati_mime_tip(d_ime)) else "application/pdf",
                        key=f"dl_opci_{d_ime}"
                    )
        else:
            st.caption("⚠️ Nema unesenih općih posjedovnih listova u bazi.")

with col_ikona2:
    with st.popover("📜 Matične Knjige"):
        st.markdown("### 🏛️ Matične knjige - državni arhiv")
        st.write("Preuzmite obiteljsku arhivu:")
        
        cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE id_cestice = 777777")
        sve_mk = cursor.fetchall()
        
        if sve_mk:
            for (sadrzaj,) in sve_mk:
                if sadrzaj and "|||" in sadrzaj:
                    d_ime, b64_kod = sadrzaj.split("|||", 1)
                    f_bajtovi = base64.b64decode(b64_kod)
                    
                    # Čistimo naziv za ljepši prikaz na gumbu (npr. "Illia.png" postaje "Illia")
                    prikaz_ime = d_ime.split('.')[0] if '.' in d_ime else d_ime
                    
                    st.download_button(
                        label=f"👶 {prikaz_ime.upper()} MLINAR",
                        data=f_bajtovi,
                        file_name=d_ime,
                        mime=dohvati_mime_tip(d_ime),
                        key=f"dl_mk_{d_ime}"
                    )
        else:
            st.caption("⚠️ Nema unesenih matičnih knjiga u bazi.")

with col_ikona3:
    with st.popover("📂 Poslani Dokumenti"):
        st.markdown("### 📁 Dokumenti od rodbine")
        
        cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE id_cestice = 999999")
        svi_poslani_doc = cursor.fetchall()
        
        if svi_poslani_doc:
            for (sadrzaj_datoteke,) in svi_poslani_doc:
                if sadrzaj_datoteke and "|||" in sadrzaj_datoteke:
                    try:
                        d_ime, b64_kod = sadrzaj_datoteke.split("|||", 1)
                        f_bajtovi = base64.b64decode(b64_kod)
                        
                        st.download_button(
                            label=f"🔹 Preuzmi: {d_ime}",
                            data=f_bajtovi,
                            file_name=d_ime,
                            mime=dohvati_mime_tip(d_ime),
                            key=f"dl_g_{d_ime}"
                        )
                    except Exception: pass
        else:
            st.info("Nema učitanih dokumenata. Iskoristite uploader na vrhu.")


# Osiguravamo da polje katastarska_opcina postoji u bazi
#try:
#    cursor.execute("ALTER TABLE cestice ADD COLUMN katastarska_opcina TEXT;")
#    conn.commit()
#except sqlite3.OperationalError:
#    pass

# --- POPRAVLJENO ZA SUPABASE (PostgreSQL) ---
try:
    # SQL naredba koja u Postgresu dodaje stupac ako on vec ne postoji
    cursor.execute("""
        ALTER TABLE cestice 
        ADD COLUMN IF NOT EXISTS katastarska_opcina TEXT;
    """)
    conn.commit()
except Exception:
    # Ako se dogodi bilo kakva greska s bazom, program ce je sigurno preskociti
    if conn:
        conn.rollback()
    pass

st.subheader("🔍 Pretraživanje")
col_f1, col_f2 = st.columns(2)

cursor.execute("SELECT id, naziv_podrucja FROM podrucja")
sva_p = cursor.fetchall()
p_dict = {naziv: id for id, naziv in sva_p}

with col_f1:
    odabrano_p = st.selectbox("Odaberi područje (lokaciju):", ["Sva područja"] + list(p_dict.keys()))

if odabrano_p == "Sva područja":
    cursor.execute("SELECT id, broj_cestice FROM cestice")
else:
    cursor.execute("SELECT id, broj_cestice FROM cestice WHERE id_podrucja = %s", (p_dict[odabrano_p],))

sve_c = cursor.fetchall()
c_dict = {broj: id for id, broj in sve_c}

with col_f2:
    odabrana_c = st.selectbox("Upiši ili odaberi broj čestice:", ["-- Prikaži sve čestice --"] + list(c_dict.keys()))

st.write("---")

if odabrana_c != "-- Prikaži sve čestice --":
    id_c = c_dict[odabrana_c]
    cursor.execute("""
        SELECT c.zk_ulozak, c.broj_zadnjeg_dnevnika, c.oznaka_zemljista, c.naziv_zemljista, c.napomena, c.povrsina, p.naziv_podrucja, c.katastarska_opcina, c.sifra
        FROM cestice c JOIN podrucja p ON c.id_podrucja = p.id WHERE c.id = %s
    """, (id_c,))

    zk, dnevnik, oznaka, naziv, napomena, povrsina, lokacija, ko, interna_sifra = cursor.fetchone()
    
    st.markdown(f"### 📍 Podaci za česticu: **{odabrana_c}** ({lokacija})")
    st.link_button("🌐 Otvori ovu česticu na Uređena Zemlja (ZIS)", "https://oss.uredjenazemlja.hr")
    st.write("")

    c1, c2, c3 = st.columns(3)
    c1.info(f"**📑 Katastarska općina (K.O.):** {ko if ko else 'Nema podatak'}\n\n**🔢 ZK Uložak:** {zk if zk else 'Nema podatak'}")
    c2.info(f"**🌿 Oznaka:** {oznaka if oznaka else 'Nema podatak'}\n\n**🗺️ Naziv:** {naziv if naziv else 'Nema podatak'}")
    c3.success(f"**📐 Površina:**\n\n### {povrsina} m²" if povrsina else "**📐 Površina:**\n\nNije upisana")
    
    # PRIKAZ INTERNE ŠIFRE/KATEGORIJE NA FRONTENDU
    st.markdown(f"**🏷️ Interna kategorija čestice:** `{interna_sifra if interna_sifra else 'Bez šifre'}`")

    st.markdown("#### 📝 Napomena o stanju čestice:")
    if napomena:
        st.markdown(f"> {napomena}")
    else:
        st.write("Nema upisanih napomena za ovu česticu.")
      
    st.write("---")
    st.markdown("### ⏳ Povijesna Arhiva Listova")
    cursor.execute("""
        SELECT vrsta_lista, broj_lista_korisnika, starost_godina, upisani_vlasnik_posjednik, povijesna_napomena, datoteka 
        FROM povijest_dokumenata WHERE id_cestice = %s
    """, (id_c,))

    stari_listovi = cursor.fetchall()
    
    if stari_listovi:
        for vrsta, broj_l, starost, vlasnik, p_nap, datoteka in stari_listovi:
            ikona = "📕" if "vlasnič" in vrsta.lower() else "📘"
            with st.expander(f"{ikona} {vrsta} — {starost if starost else 'Nepoznata godina'} (Broj: {broj_l})"):
                st.markdown(f"**👤 Upisana osoba:** {vlasnik if vlasnik else '/'}")
                st.markdown(f"**🔍 Povijesna bilješka:** {p_nap if p_nap else '/'}")
                
                # --- NOVI, NEPROBOJAN PRIKAZ DOKUMENATA IZ SQL TEKSTA (Base64) UNUTAR EXPANDERA ---
                if datoteka:
                    try:
                        if "|||" in datoteka:
                            naziv_datoteke, b64_sadrzaj = datoteka.split("|||", 1)
                            izvorni_bajtovi = base64.b64decode(b64_sadrzaj)
                            
                            if naziv_datoteke.lower().endswith(('.jpg', '.jpeg', '.png')):
                                st.image(izvorni_bajtovi, caption=f"Dokument: {naziv_datoteke}", use_container_width="always")
                            
                            elif naziv_datoteke.lower().endswith('.pdf'):
                                # PDF prozor bez ikakvih gumba za preuzimanje na uređaj
                                pdf_prikaz = f'<iframe src="data:application/pdf;base64,{b64_sadrzaj}" width="100%" height="600" type="application/pdf"></iframe>'
                                st.markdown(pdf_prikaz, unsafe_allow_html=True)
                        else:
                            # Prikaz poruke ako je u pitanju stari zapis iz prve faze testiranja aplikacije
                            st.caption(f"📄 Vezana stara lokalna datoteka: {datoteka}")
                    except Exception as e:
                        st.error(f"❌ Greška prilikom učitavanja dokumenta: {e}")
    else:
        st.warning("U arhivi trenutno nema starih listova vezanih uz ovu česticu.")

# --- POTPUNO POPRAVLJENO I SIGURNO ZA SUPABASE I PANDAS ---
else:
    st.markdown(f"### 📋 Popis čestica za odabir: *{odabrano_p}*")
    if sve_c:
        import pandas as pd
        
        if odabrano_p == "Sva područja":
            upit = """
                SELECT c.broj_cestice, c.zk_ulozak, c.broj_zadnjeg_dnevnika, c.katastarska_opcina, p.naziv_podrucja, c.oznaka_zemljista, c.povrsina
                FROM cestice c 
                JOIN podrucja p ON c.id_podrucja = p.id
            """
            df = pd.read_sql_query(upit, conn)
        else:
            upit = """
                SELECT c.broj_cestice, c.zk_ulozak, c.broj_zadnjeg_dnevnika, c.katastarska_opcina, p.naziv_podrucja, c.oznaka_zemljista, c.povrsina
                FROM cestice c 
                JOIN podrucja p ON c.id_podrucja = p.id
                WHERE c.id_podrucja = %s
            """
            df = pd.read_sql_query(upit, conn, params=(p_dict[odabrano_p],))
        
        preimenovani_stupci = {
            "broj_cestice": "Broj čestice",
            "zk_ulozak": "Broj ZK uloška",
            "broj_zadnjeg_dnevnika": "Broj zadnjeg dnevnika",
            "katastarska_opcina": "Katastarska općina",
            "naziv_podrucja": "Područje",
            "oznaka_zemljista": "Oznaka",
            "povrsina": "Površina (m²)"
        }
        df = df.rename(columns=preimenovani_stupci)
        
        st.dataframe(df, width='stretch', hide_index=True)
        
        ukupna_povrsina = pd.to_numeric(df['Površina (m²)'], errors='coerce').fillna(0).sum()
        
        st.write("")
        col_prazan1, col_prazan2, col_Desno = st.columns([2, 2, 1])
        
        with col_Desno:
            st.metric(
                label=f"📐 Ukupna površina ({odabrano_p}):", 
                value=f"{int(ukupna_povrsina):,}".replace(",", " ") + " m²"
            )
            
    else:
        st.info("Nema unesenih čestica za prikaz.")

conn.close()
