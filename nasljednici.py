import streamlit as st
import pandas as pd
from zoneinfo import ZoneInfo

def obradi_klik_rodbe(cursor, conn, ip_adresa, popis_slobodnih_id):
    if "editor_interesa_v2" in st.session_state and st.session_state["editor_interesa_v2"]["edited_rows"]:
        promjene = st.session_state["editor_interesa_v2"]["edited_rows"]
        broj_promjena = 0
        
        for indeks_retka, izmjena in promjene.items():
            if "Odaberi" in izmjena:
                indeks_int = int(indeks_retka)
                
                # Kirurski precizno izvlacenje ID-a iz ciste Python liste, bez Pandasa!
                cid = int(popis_slobodnih_id[indeks_int])
                
                # Broj cestice povlacimo sigurno iz baze podataka
                cursor.execute("SELECT broj_cestice FROM cestice WHERE id = %s", (cid,))
                rezultat_broja = cursor.fetchone()
                broj = str(rezultat_broja[0]) if rezultat_broja else "Nepoznato"
                
                nova_vrijednost = bool(izmjena["Odaberi"])
                if nova_vrijednost:
                    # Korisnik je ukljucio kvacicu -> upisujemo u bazu i logove
                    cursor.execute("""
                        INSERT INTO dioba_cestica (id_cestice, oznacena, status_diobe) 
                        VALUES (%s, TRUE, 'Interes')
                        ON CONFLICT (id_cestice) DO UPDATE SET oznacena = TRUE,status_diobe = 'Interes'
                    """, (cid,))
                    cursor.execute("INSERT INTO log_diobe_cestica (id_cestice, broj_cestice, akcija, ip_adresa) VALUES (%s, %s, 'KLIKNUTO', %s)", (cid, broj, ip_adresa))
                    broj_promjena += 1
                else:
                    # Korisnik je iskljucio kvacicu -> brisemo iz baze i logiramo
                    cursor.execute("DELETE FROM dioba_cestica WHERE id_cestice = %s", (cid,))
                    cursor.execute("INSERT INTO log_diobe_cestica (id_cestice, broj_cestice, akcija, ip_adresa) VALUES (%s, %s, 'ODKLIKNUTO', %s)", (cid, broj, ip_adresa))
                    broj_promjena += 1
                    
        if broj_promjena > 0:
            conn.commit()
      

def prikazi_ekran_nasljednika(cursor, conn):
    st.title("👥 Iskazivanje interesa za čestice")
    st.write("Označite kvačicom čestice za koje iskazujete interes.")

    # 1. ČITANJE IP ADRESE KORISNIKA 
    try:
        # Streamlit 1.30+ službeni način za čitanje IP adrese preko zaglavlja servera
        ip_adresa = st.context.headers.get("x-forwarded-for", "127.0.0.1").split(",")[0].strip()
    except Exception:
        ip_adresa = "Nepoznata IP"

    # =========================================================================
    # 🗺️ GORNJI DIO: TABLICA ZA ISKAZIVANJE INTERESA (AUTOMATSKO SPREMANJE)
    # =========================================================================
    

    # 2. DOHVAĆANJE SVIH ČESTICA IZ BAZE
    cursor.execute("""
        SELECT c.id, c.broj_cestice, c.zk_ulozak, p.naziv_podrucja, c.oznaka_zemljista, c.naziv_zemljista, c.napomena, c.zona, c.povrsina 
        FROM cestice c
        JOIN podrucja p ON c.id_podrucja = p.id
        LEFT JOIN dioba_cestica dc ON c.id = dc.id_cestice
        WHERE c.id NOT IN (999999, 777777) AND (dc.status_diobe IS NULL OR dc.status_diobe != 'Dodijeljeno')
        ORDER BY c.broj_cestice
    """)
    sve_cestice = cursor.fetchall()


    # 3. DOHVAĆANJE TRENUTNO OZNAČENIH ČESTICA IZ BAZE 
    cursor.execute("SELECT id_cestice, status_diobe FROM dioba_cestica")
    #stanja_iz_baze = {int(red[0]): str(red[1]).strip() for red in cursor.fetchall() if red}
        # 🔥 POPRAVLJENO: Točno izvlačimo ID (indeks 0) i stvarni status (indeks 1) iz baze podataka
    stanja_iz_baze = {int(red[0]): str(red[1]).strip() for red in cursor.fetchall() if red and red[0] is not None and red[1] is not None}

    trenutno_oznacene_ids = set(stanja_iz_baze.keys())


    trenutno_oznacene_ids = set(stanja_iz_baze.keys())
    #"Odaberi": True if status_c == "Dodijeljeno" else (cid in trenutno_oznacene_ids),




    # 4. Priprema konfiguracije stupaca i dinamickog popisa za zakljucavanje
    konfiguracija_kolona = {
        "Broj čestice": st.column_config.Column(disabled=True),
        "ZK Uložak": st.column_config.Column(disabled=True),
        "Podrucje": st.column_config.Column(disabled=True),
        "Oznaka zemljišta": st.column_config.Column(disabled=True),
        "Naziv zemljišta": st.column_config.Column(disabled=True),
        "Napomena": st.column_config.Column(disabled=True),
        "Zona": st.column_config.Column(disabled=True),
        "Površina (m2)": st.column_config.Column(disabled=True),
        "SKRIVENI_ID": None
    }
    
    podaci_slobodno = []
    podaci_dodijeljeno = []
    podaci_za_tablicu = []
 

    # 4. PRIPREMA PANDAS DATAFRAME-A 
    for indeks_retka, (cid, broj, zk, podrucje_naziv, oznaka, naziv, napomena, zon, povrsina) in enumerate(sve_cestice):
        # 🔥 2. KORAK: Cita cisti tekst ('Interes' ili 'Dodijeljeno') ili vraca None ako je nema u bazi
        status_trenutni = stanja_iz_baze.get(cid, None)
        is_checked = cid in trenutno_oznacene_ids


        podaci_za_tablicu.append({
            "Odaberi": is_checked,
            "Broj čestice": broj,
            "ZK Uložak": str(zk) if zk else "-",
            "Područje": str(podrucje_naziv) if podrucje_naziv else "-",
            "Oznaka zemljišta": oznaka if oznaka else "-",
            "Naziv zemljišta": naziv if naziv else "-",
            "Napomena": napomena if napomena else "-",
            "Zona": zon if zon else "-",
            "Površina (m2)": float(povrsina) if povrsina else 0.0,
            "SKRIVENI_ID": cid
        })        


                # 🔥 PROVJERENO PORAVNANJE NA KRAJU PETLJE (0% kvacica)
        #status_cisti = str(status_trenutni).strip().upper() if status_trenutni else ""
        
               # 🔥 POPRAVLJENO: Sve cestice inicijalno punimo u slobodni popis (0% kvacica)
        podaci_slobodno.append(podaci_za_tablicu[-1])



    df_sve = pd.DataFrame(podaci_za_tablicu)
    
    # Primjenjuje sivi i zakljucani status na stupac Odaberi
    konfiguracija_kolona["Odaberi"] = st.column_config.CheckboxColumn(
        "Odaberi", 
        default=False,
    )



    # 5. TABLICA S INSTANT OKIDAČEM PROMJENA (Bez rušenja Fullscreen prikaza)
        # ZADNJI KORAK: Ugradnja tabova i razdvajanje prikaza (0% kvacica)
    tab_slobodno, tab_dodijeljeno = st.tabs(["👥 Slobodne čestice za odabir", "🔒 Dodijeljene čestice"])

    with tab_slobodno:
        df_slobodno = pd.DataFrame(podaci_slobodno) if podaci_slobodno else pd.DataFrame(columns=df_sve.columns)
        lista_slobodnih_id = [int(r["SKRIVENI_ID"]) for r in podaci_slobodno]

        uredjeni_df = st.data_editor(
            df_slobodno,
            hide_index=True,
            disabled=["Broj čestice", "ZK Uložak", "Područje", "Oznaka zemljišta", "Naziv zemljišta", "Napomena", "Zona", "Površina (m2)"],
            width="stretch",
            column_config={
                "Odaberi": st.column_config.CheckboxColumn("Odaberi", default=False),
                "SKRIVENI_ID": None
            },
            key="editor_interesa_v2",
            on_change=obradi_klik_rodbe,
            args=(cursor, conn, ip_adresa, lista_slobodnih_id)
        )

    with tab_dodijeljeno:
        # 🔥 POPRAVLJENO: Drugi tab sam iz baze cupa iskljucivo sluzbeno dodijeljene parcele!
        cursor.execute("""
            SELECT c.broj_cestice, c.zk_ulozak, p.naziv_podrucja, c.oznaka_zemljista, c.naziv_zemljista, c.povrsina, dc.nasljednik
            FROM dioba_cestica dc
            JOIN cestice c ON dc.id_cestice = c.id
            JOIN podrucja p ON c.id_podrucja = p.id
            WHERE dc.status_diobe = 'Dodijeljeno'
            ORDER BY c.broj_cestice
        """)
        dodijeljene_iz_baze = cursor.fetchall()

        if dodijeljene_iz_baze:
            podaci_za_tablicu_b = []
            for broj, zk, podrucje, oznaka, naziv, povrsina, nasljednik in dodijeljene_iz_baze:
                podaci_za_tablicu_b.append({
                    "Broj čestice": broj,
                    "ZK Uložak": str(zk) if zk else "-",
                    "Područje": podrucje,
                    "Oznaka zemljišta": oznaka if oznaka else "-",
                    "Naziv zemljišta": naziv if naziv else "-",
                    "Površina (m2)": float(povrsina) if povrsina else 0.0,
                    "Kome pripada": nasljednik if nasljednik else "Nije dodijeljeno"
                })
            
            df_dodijeljeno_konacno = pd.DataFrame(podaci_za_tablicu_b)
            
            st.data_editor(
                df_dodijeljeno_konacno,
                hide_index=True,
                disabled=True, # Potpuno sivo i zakljucano za rodbinu
                width="stretch",
                key="editor_zakljucanih_konacno"
            )
        else:
            st.caption("Nema sluzbeno dodijeljenih cestica.")

   
       # =========================================================================
    #  HISTORIJSKI LOGOVI S AUTOMATSKIM PREBACIVANJEM U LOKALNO VRIJEME (EUROPE/ZAGREB)
    # =========================================================================
    st.write("---")
    
    with st.expander("📜 Povijest svih odabira i promjena "):
            cursor.execute("SELECT vrijeme_promjene, broj_cestice, akcija, ip_adresa FROM log_diobe_cestica ORDER BY id DESC LIMIT 100")
            logovi = cursor.fetchall()
            
            if logovi:
                # Uvozimo službenu Python biblioteku za vremenske zone
                from zoneinfo import ZoneInfo
                
                for vrijeme_server, broj, akcija, ip in logovi:
                    # 1. Kažemo Pythonu da je vrijeme iz baze UTC (serversko)
                    vrijeme_utc = vrijeme_server.replace(tzinfo=ZoneInfo("UTC"))
                    # 2. Preračunavamo ga u točnu hrvatsku vremensku zonu (pazi na ljetno/zimsko vrijeme!)
                    vrijeme_lokalno = vrijeme_utc.astimezone(ZoneInfo("Europe/Zagreb"))
                    
                    # 3. Ispisujemo prelijepo formatirano lokalno vrijeme na ekranu
                    st.markdown(f"⏱️ `{vrijeme_lokalno.strftime('%d.%m.%Y. %H:%M:%S')}` | 📍 Čestica: **{broj}** → Oznaka: `{akcija}` (IP: `{ip}`)")
            else:
                st.caption("Nema zabilježenih povijesnih promjena u bazi podataka.")
