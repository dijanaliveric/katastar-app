import os
import psycopg2
import streamlit as st
from PIL import Image
import urllib.parse
import warnings

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

# Dodajemo dinamički ključ 
datoteka = st.file_uploader(
    "Učitaj dokument",
    type=["png", "jpg", "jpeg", "pdf", "xlsx", "docx"],
    key=f"glavni_gornji_uploader_{st.session_state['uploader_kljuc']}",
)
# Kada rodbina ubaci dokument
if datoteka is not None:
    # 1. ZAŠTITA: Provjera ekstenzije u kodu za svaki slučaj
    ekstenzija = datoteka.name.split(".")[-1].lower()
    if ekstenzija not in ["png", "jpg", "jpeg", "pdf", "xlsx", "docx"]:
        st.error("❌ Greška: Ovaj format datoteke nije dozvoljen za prijenos!")
    else:
        # 2. ZAŠTITA: Uhvati bilo kakvu grešku pri pisanju na disk (npr. pun disk, krivi znakovi u nazivu)
        try:
            putanja_za_spremiti = os.path.join(upload_mapa, datoteka.name)
            with open(putanja_za_spremiti, "wb") as f:
                f.write(datoteka.getbuffer())
            
            st.success(f"Uspjesno spremljeno: {datoteka.name}")
            
            # Resetiranje uploadera i osvježavanje stranice
            st.session_state["uploader_kljuc"] += 1
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Doslo je do nepredvidjene greske prilikom spremanja datoteke. Pokusajte ponovno.")
st.write("---")

# --- OSNOVNE POSTAVKE ---
st.set_page_config(page_title="Katastar Arhiva - Pregled", layout="wide")
st.title("🗺️ Obiteljska Arhiva Zemljišta i Čestica")

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


# --- FIKSNI GUMBI ZA OPĆE DOKUMENTE I MATIČNE KNJIGE ---
col_ikona1, col_ikona2, col_ikona3, _ = st.columns([1, 1, 1, 4])  # Stvara dva stupca s lijeve strane

with col_ikona1:
    with st.popover("📋 Posjedovni Listovi"):
        st.markdown("### 📄 Opći katastarski dokumenti")
        st.write("Preuzmite posjedovne listove:")
        try:
            with open("dokumenti/posjedovni_list_1.pdf", "rb") as f1:
                st.download_button("📥 Posjedovni list - 1. dio (PDF)", data=f1.read(), file_name="posjedovni_list_1.pdf", mime="application/pdf", key="glavni_pl_1")
        except FileNotFoundError:
            st.caption("⚠️ Datoteka 'posjedovni_list_1.pdf' nije pronađena.")
            
        try:
            with open("dokumenti/posjedovni_list_2.pdf", "rb") as f2:
                st.download_button("📥 Posjedovni list - 2. dio (PDF)", data=f2.read(), file_name="posjedovni_list_2.pdf", mime="application/pdf", key="glavni_pl_2")
        except FileNotFoundError:
            st.caption("⚠️ Datoteka 'posjedovni_list_2.pdf' nije pronađena.")

with col_ikona2:
    # ---  MATIČNE KNJIGE ---
    with st.popover("📜 Matične Knjige"):
        st.markdown("### 🏛️ Matične knjige - državni arhiv Zadar")
        st.write("Preuzmite obiteljsku arhivu:")
        
        try:
            with open("dokumenti/maticne_knjige/Illia.png", "rb") as f_rodj:
                st.download_button("👶 ILLIA MLINAR", data=f_rodj.read(), file_name="Illia.png", mime="application/png", key="mk_illia")
        except FileNotFoundError:
            st.caption("⚠️ Datoteka 'Illia.png' nije pronađena u mapi 'maticne_knjige'.")
            
      
        try:
            with open("dokumenti/maticne_knjige/Jandria.png", "rb") as f_rodj:
                st.download_button("👶 JANDRIA MLINAR", data=f_rodj.read(), file_name="Jandria.png", mime="application/png", key="mk_jandria")
        except FileNotFoundError:
            st.caption("⚠️ Datoteka 'Jandria.png' nije pronađena u mapi 'maticne_knjige'.")

        try:
            with open("dokumenti/maticne_knjige/Vasilj.png", "rb") as f_rodj:
                st.download_button("👶 VASILJ MLINAR", data=f_rodj.read(), file_name="Vasilj.png", mime="application/png", key="mk_vasilj")
        except FileNotFoundError:
            st.caption("⚠️ Datoteka 'Vasilj.png' nije pronađena u mapi 'maticne_knjige'.")
    

        try:
            with open("dokumenti/maticne_knjige/Josip.png", "rb") as f_rodj:
                st.download_button("👶 JOSIP MLINAR", data=f_rodj.read(), file_name="Josip.png", mime="application/png", key="mk_josip")
        except FileNotFoundError:
            st.caption("⚠️ Datoteka 'Josip.png' nije pronađena u mapi 'maticne_knjige'.")
            
      
        try:
            with open("dokumenti/maticne_knjige/Jovan.png", "rb") as f_rodj:
                st.download_button("👶 JOVAN MLINAR", data=f_rodj.read(), file_name="Jovan.png", mime="application/png", key="mk_jovan")
        except FileNotFoundError:
            st.caption("⚠️ Datoteka 'Jovan.png' nije pronađena u mapi 'maticne_knjige'.")


with col_ikona3:
    with st.popover("📂 Dokumenti"):
        st.markdown("### 📁 Pregled Obiteljskih Dokumenta")
        st.write("Preuzmite obiteljske dokumente:")

        sve_datoteke = os.listdir(upload_mapa)
        if sve_datoteke:
            for datoteka_ime in sve_datoteke:
                putanja_datoteke = os.path.join(upload_mapa, datoteka_ime)
                try:
                    with open(putanja_datoteke, "rb") as f_preuzmi:
                        st.download_button(
                            label=f"🔹 Preuzmi: {datoteka_ime}",
                            data=f_preuzmi.read(),
                            file_name=datoteka_ime,
                            key=f"dl_gornji_{datoteka_ime}",
                        )
                except Exception:
                    pass
        else:
            st.info("Nema ucitanih dokumenata. Iskoristite uploader na vrhu.")

st.write("---")

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
        SELECT c.zk_ulozak, c.broj_zadnjeg_dnevnika, c.oznaka_zemljista, c.naziv_zemljista, c.napomena, c.povrsina, p.naziv_podrucja, c.katastarska_opcina
        FROM cestice c JOIN podrucja p ON c.id_podrucja = p.id WHERE c.id = %s
    """, (id_c,))

    
    zk, dnevnik, oznaka, naziv, napomena, povrsina, lokacija, ko = cursor.fetchone()
    
    st.markdown(f"### 📍 Podaci za česticu: **{odabrana_c}** ({lokacija})")
    

    st.link_button("🌐 Otvori ovu česticu na Uređena Zemlja (ZIS)", "https://oss.uredjenazemlja.hr")
    st.write("")

    c1, c2, c3 = st.columns(3)
    c1.info(f"**📑 ZK Uložak:** {zk if zk else 'Nema podatak'}\n\n**🔢 Zadnji dnevnik:** {dnevnik if dnevnik else 'Nema podatak'}")
    c2.info(f"**🌿 Oznaka:** {oznaka if oznaka else 'Nema podatak'}\n\n**🗺️ Naziv:** {naziv if naziv else 'Nema podatak'}")
    c3.success(f"**📐 Površina:**\n\n### {povrsina} m²" if povrsina else "**📐 Površina:**\n\nNije upisana")
    
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
            with st.expander(f"{ikona} {vrsta} — {starost} (Broj: {broj_l})"):
                st.markdown(f"**👤 Upisana osoba:** {vlasnik}")
                st.markdown(f"**🔍 Povijesna bilješka:** {p_nap}")
                # --- NOVI DIO ZA IZRAVNI PRIKAZ JPG ILI PDF DATOTEKA NA EKRANU ---
            if datoteka:
                putanja = f"dokumenti/{datoteka}"
                            # --- PRIVREMENI KOD ZA OTKRIVANJE GREŠKE ---
            if datoteka:
                putanja = f"dokumenti/{datoteka}"       
                               
                if datoteka.lower().endswith(('.jpg', '.jpeg', '.png')):
                    st.image(putanja, caption=f"Skenirani dokument: {datoteka}", use_container_width="always")
                
                elif datoteka.lower().endswith('.pdf'):
                    import base64
                    with open(putanja, "rb") as f:
                        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    
                    pdf_prikaz = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                    st.markdown(pdf_prikaz, unsafe_allow_html=True)

            
    else:
        st.warning("U arhivi trenutno nema starih listova vezanih uz ovu česticu.")


# --- POTPUNO POPRAVLJENO I SIGURNO ZA SUPABASE I PANDAS ---
else:
    st.markdown(f"### 📋 Popis čestica za odabir: *{odabrano_p}*")
    if sve_c:
        import pandas as pd
        
        # Uklonili smo sve komplicirane alias-e i navodnike iz samog SQL-a
        # Pandas će sam preuzeti čiste nazive stupaca iz baze
        if odabrano_p == "Sva područja":
            upit = """
                SELECT c.broj_cestice, c.zk_ulozak, c.broj_zadnjeg_dnevnika, c.katastarska_opcina, p.naziv_podrucja, c.oznaka_zemljista, c.povrsina
                FROM cestice c 
                JOIN podrucja p ON c.id_podrucja = p.id
            """
            df = pd.read_sql_query(upit, conn)
        else:
            # Koristimo siguran %s parametar za PostgreSQL
            upit = """
                SELECT c.broj_cestice, c.zk_ulozak, c.broj_zadnjeg_dnevnika, c.katastarska_opcina, p.naziv_podrucja, c.oznaka_zemljista, c.povrsina
                FROM cestice c 
                JOIN podrucja p ON c.id_podrucja = p.id
                WHERE c.id_podrucja = %s
            """
            df = pd.read_sql_query(upit, conn, params=(p_dict[odabrano_p],))
        
        # Ručno i sigurno preimenujemo stupce u Pandasu nakon što su podaci već učitani
        # Na ovaj način zaobilazimo sve SQL sintaksne greške i kvačice!
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
        
        # 1. Prikaz tablice rastegnute preko ekrana pomoću provjerene i stabilne sintakse
        st.dataframe(df, width='stretch', hide_index=True)
        
        # 2. Izračun ukupne površine (sada tražimo točan naziv stupca koji smo gore preimenovali)
        ukupna_povrsina = pd.to_numeric(df['Površina (m²)'], errors='coerce').fillna(0).sum()
        
        # 3. Prikaz metričke kartice u desnom poravnanju
        st.write("")
        col_prazan1, col_prazan2, col_Desno = st.columns([2, 2, 1]) # Koristimo čiste brojeve za omjere stupaca
        
        with col_Desno:
            st.metric(
                label=f"📐 Ukupna površina ({odabrano_p}):", 
                value=f"{int(ukupna_povrsina):,}".replace(",", " ") + " m²"
            )
            
    else:
        st.info("Nema unesenih čestica za prikaz.")



        # --- SPAJANJE USER I ADMIN DJELA U JEDAN LINK ---
st.sidebar.write("---")
izbor_stranice = st.sidebar.radio("🧭 Izbornik:", ["🗺️ Pregled čestica", "🔐 Administracija"])

if izbor_stranice == "🔐 Administracija":
    # Ako kliknete na admina, provjeravamo admin lozinku iz secrets.toml
    if "admin_autentificiran" not in st.session_state:
        st.session_state["admin_autentificiran"] = False

    if not st.session_state["admin_autentificiran"]:
        st.subheader("🔐 Kontrolna ploča - Administracija")
        u_admin_korisnik = st.text_input("Admin Korisničko ime:", key="web_admin_user")
        u_admin_lozinka = st.text_input("Admin Lozinka:", type="password", key="web_admin_pass")
        
        if st.button("Prijavi se u sustav", key="web_admin_btn"):
            if u_admin_korisnik == st.secrets["admin_credentials"]["username"] and u_admin_lozinka == st.secrets["admin_credentials"]["password"]:
                st.session_state["admin_autentificiran"] = True
                st.rerun()
            else:
                st.error("❌ Nevžeće administratorske lozinke.")
        st.stop()

    # Ako je lozinka točna, učitavamo vaše module izravno na ekran
    from admin_unos import prikazi_unos
    from admin_uredi import prikazi_uredivanje
    from admin_brisi import prikazi_brisanje
    
    # Ponovno dohvaćamo čestice za admin izbornike
    cursor.execute("SELECT id, broj_cestice FROM cestice")
    c_glavni_dict = {broj: id for id, broj in cursor.fetchall()}
    
        # Ako je lozinka točna, učitavamo vaše module izravno na ekran
    from admin_unos import prikazi_unos
    from admin_uredi import prikazi_uredivanje
    from admin_brisi import prikazi_brisanje
    
    # Ponovno dohvaćamo čestice za admin izbornike
    cursor.execute("SELECT id, broj_cestice FROM cestice")
    c_glavni_dict = {broj: id for id, broj in cursor.fetchall()}
    
    # POPRAVLJENO: Stvaramo p_obrnuti_dict koji nedostaje u app.py
    p_obrnuti_dict = {id: naziv for id, naziv in sva_p}
    
    tab_glavni1, tab_glavni2, tab_glavni3 = st.tabs(["➕ Unos Podataka", "✍️ Uredi Česticu", "❌ Brisanje Podataka"])
    with tab_glavni1: prikazi_unos(conn, cursor, sva_p, p_dict)
    with tab_glavni2: prikazi_uredivanje(conn, cursor, c_glavni_dict, p_dict, p_obrnuti_dict)
    with tab_glavni3: prikazi_brisanje(conn, cursor, c_glavni_dict)

    tab_glavni1, tab_glavni2, tab_glavni3 = st.tabs(["➕ Unos Podataka", "✍️ Uredi Česticu", "❌ Brisanje Podataka"])
    with tab_glavni1: prikazi_unos(conn, cursor, sva_p, p_dict)
    with tab_glavni2: prikazi_uredivanje(conn, cursor, c_glavni_dict, p_dict, p_obrnuti_dict)
    with tab_glavni3: prikazi_brisanje(conn, cursor, c_glavni_dict)


conn.close()
