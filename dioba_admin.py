import streamlit as st
import pandas as pd
import json
import psycopg2
from zoneinfo import ZoneInfo


    # =========================================================================
    # ⚖️ KUTAK ZA ADMINA I ODVJETNIKA (MINIMALISTIČKA DODJELA)
    # =========================================================================
def prikazi_ekran_administracije(cursor, conn):
    try:
        ip_adresa = st.context.headers.get("x-forwarded-for", "127.0.0.1").split(",")[0].strip()
    except Exception:
        ip_adresa = "127.0.0.1"



    je_admin = st.query_params.get("admin") == "da"

    if je_admin:
        st.write("---")
        st.markdown("### ⚖️ Kutak za upravljanje diobom (Administrator i Odvjetnik)")
        st.write("Odaberite nasljednika iz padajućeg izbornika unutar tablice za konačnu dodjelu imovine:")

        
        # 1. Povlači sve unesene nasljednike iz baze podataka
        cursor.execute("SELECT id, id_prednika, ime_prednika, ime_nasljednika, red_nasljedstva, odrekao_se, u_korist_id FROM popis_nasljednika ORDER BY id_prednika ASC, red_nasljedstva ASC, id ASC")
        svi_nasljednici_baza = cursor.fetchall()

        # 2. AUTOMATIKA: Sustav sam broji koliko ukupno ima obiteljskih grana u ovoj diobi (npr. koliko je braće/sestara)
        jedinstvene_grane = set([r[1] for r in svi_nasljednici_baza])
        broj_ukupnih_grana = len(jedinstvene_grane) if jedinstvene_grane else 1
        
        # Svaka grana dobiva potpuno jednak dio imanja (100% podijeljeno s brojem grana)
        vrijednost_jedne_grane = 100.0 / broj_ukupnih_grana

        # 3. Broji koliko ima aktivnih (ne-odrečenih) ljudi unutar svake pojedine grane
        aktivni_u_grani = {}
        ukupno_u_grani = {}
        for _, grana_id, _, _, _, odr, _ in svi_nasljednici_baza:
            ukupno_u_grani[grana_id] = ukupno_u_grani.get(grana_id, 0) + 1
            if not odr:
                aktivni_u_grani[grana_id] = aktivni_u_grani.get(grana_id, 0) + 1

        # 4. Računa koliko vrijedi osnovni udio svake osobe prije odricanja
        vrijednost_osobe_id = {}
        prijenosi_odricanja_id = {} # Skuplja postotke koji se prepisuju drugima preko ID-a

        for hid, grana_id, prednik, ime, red, odr, u_korist_id in svi_nasljednici_baza:
            broj_aktivnih = aktivni_u_grani.get(grana_id, 0)
            
            # Ako u grani ima aktivnih, vrijednost grane se dijeli na njih. 
            # Ako su se svi u toj grani odrekli, računamo vrijednost pojedinca da znamo koliko prenosi dalje
            if broj_aktivnih > 0:
                osnovni_udio = vrijednost_jedne_grane / broj_aktivnih if not odr else 0.0
                vrijednost_za_prijenos = vrijednost_jedne_grane / broj_aktivnih
            else:
                broj_ljudi = ukupno_u_grani.get(grana_id, 1)
                osnovni_udio = 0.0
                vrijednost_za_prijenos = vrijednost_jedne_grane / broj_ljudi

            vrijednost_osobe_id[hid] = osnovni_udio

            # Ako se osoba odrekla u korist nekog ID-a iz tablice:
            if odr and u_korist_id:
                target_id = int(u_korist_id)
                # Pribrajamo vrijednost njezina udjela direktno toj osobi preko ID ključa
                prijenosi_odricanja_id[target_id] = prijenosi_odricanja_id.get(target_id, 0.0) + vrijednost_za_prijenos

        # 5. Generiramo čisti popis za padajući izbornik (Osnovni dio + naslijeđeno odricanje preko ID-a)
        popis_nasljednika = [""]
        for hid, grana_id, prednik, ime, red, odr, u_korist_id in svi_nasljednici_baza:
            if not odr: # U tablicu za dodjelu parcela idu samo oni koji primaju imovinu
                konacni_posto = vrijednost_osobe_id[hid] + prijenosi_odricanja_id.get(hid, 0.0)
                red_oznaka = f"{red}. red"
                
                # Ako je osoba dobila postotke odricanja preko ID-a, to odvjetniku jasno naznačimo
                dodatak_tekst = " + prijenos odricanja" if hid in prijenosi_odricanja_id else ""
                lijepi_prikaz = f"{prednik} ({red_oznaka}) -> {ime} [Udio: {konacni_posto:.2f}%{dodatak_tekst}]"
                popis_nasljednika.append(lijepi_prikaz)
            
           #================================================================================================
                #   ALAT ZA UPRAVLJANJE LJUDIMA I PROMJENU STATUSA
           #================================================================================================     
        with st.expander("🛠️ Otvori upravljanje nasljednicima i šifrarnikom (Unos / Odricanje / Brisanje)"):
            col_admin1, col_admin2 = st.columns(2)
            
            with col_admin1:
                st.markdown("**➕ Dodaj novog nasljednika (Bilo koji red):**")
                novo_ime = st.text_input("Ime i prezime nasljednika:", placeholder="npr. UNUK ANTE", key="adm_novo_ime")
                
                # Dinamički izvlači sva postojeća imena prednika iz baze za padajući izbornik
                grane_iz_baze = {}
                for _, grana_id, prednik_ime, _, _, _, _ in svi_nasljednici_baza:
                    grane_iz_baze[prednik_ime] = grana_id
                
                # Razvrstavamo imena abecedno radi lakšeg snalaženja
                popis_grana_imena = sorted(list(grane_iz_baze.keys()))
                
                # Korisnik na ekranu vidi isključivo IME, a ne hladne brojeve!
                odabrano_ime_prednika = st.selectbox("Pripada obiteljskoj grani (Prednik):", popis_grana_imena, key="adm_nova_grana")
                
                # Iz rječnika automatski u pozadini izvlačimo broj grane za bazu
                nova_grana = grane_iz_baze[odabrano_ime_prednika]
                novi_prednik = odabrano_ime_prednika
                
                novi_red = st.selectbox("Red nasljedstva (Generacija):", [1, 2, 3], index=1, key="adm_novi_red")
                
                if st.button("💾 Zapiši novog nasljednika", key="btn_adm_add_nasl", width="stretch"):
                    if novo_ime.strip() != "":
                        cursor.execute("""
                            INSERT INTO popis_nasljednika (id_prednika, ime_nasljednika, broj_grane, ime_prednika, red_nasljedstva, odrekao_se) 
                            VALUES (%s, %s, %s, %s, %s, FALSE)
                        """, (int(nova_grana), str(novo_ime.strip().upper()), int(nova_grana), str(novi_prednik), int(novi_red)))
                        conn.commit()
                        st.success(f"✅ {novo_ime.strip().upper()} uspješno dodan!")
                        st.rerun()
            with col_admin2:
                st.markdown("**🔄 Promijeni status odricanja (U korist nekoga):**")
                
                # Popis za administraciju u izborniku
                ljudi_opcije = {}
                popis_aktivnih_za_korist = {} # Ovdje čuvamo samo žive ljude za prijenos udjela        
                id_u_ime = {redak[0]: redak[3] for redak in svi_nasljednici_baza}

                # 2. KORAK: Punimo opcije za prikaz s točnim imenom u korist koga se odriče
                for lid, grana_id, pred, ime_n, red, odr, kor in svi_nasljednici_baza:
                    status_tekst = "❌ ODREKAO SE" if odr else "✅ AKTIVAN"
                    
                    if odr and kor:
                        ime_korisnika = id_u_ime.get(kor, f"ID: {kor}")
                        status_tekst = f"❌ U KORIST: {ime_korisnika}"
                        
                    ljudi_opcije[f"{pred} -> {ime_n} [{status_tekst}]"] = (lid, odr, ime_n)
                    
                    # U ovaj popis idu samo živi i aktivni ljudi koji mogu primiti odricanje
                    if not odr:
                        popis_aktivnih_za_korist[f"{pred} -> {ime_n}"] = lid
                    
                odabrana_osoba = st.selectbox("Odaberite člana obitelji za izmjenu:", [""] + list(ljudi_opcije.keys()), key="adm_sel_osoba")

                if odabrana_osoba != "":
                    osoba_id, trenutno_odrekao, trenutno_ime = ljudi_opcije[odabrana_osoba]
                    
                    if not trenutno_odrekao:
                        opcije_imena_korist = [x for x in popis_aktivnih_za_korist.keys() if popis_aktivnih_za_korist[x] != osoba_id]
                        u_korist_odabir = st.selectbox("Odriče se U KORIST (Odaberite osobu):", ["Nitko - dijeli se svima"] + opcije_imena_korist, key="adm_u_korist_sel")
                        
                        if st.button("🚷 Potvrdi odricanje imovine", key="btn_adm_set_odr", width="stretch"):
                            # Ako je odabrana osoba, iz rječnika čitamo njezin ID za bazu podataka
                            korist_id_baza = popis_aktivnih_za_korist[u_korist_odabir] if u_korist_odabir != "Nitko - dijeli se svima" else None
                            
                            cursor.execute("UPDATE popis_nasljednika SET odrekao_se = TRUE, u_korist_id = %s WHERE id = %s", (korist_id_baza, osoba_id))
                            conn.commit()
                            st.success("Osoba označena kao odričena. Matematika i postoci su trenutno prebačeni!")
                            st.rerun()
                    else:
                        # Ako je osoba već odričena, nudimo gumb za poništavanje i povratak u aktivne
                        if st.button("✅ Vrati osobu u aktivne (Poništi odricanje)", key="btn_adm_reset_odr", width="stretch"):
                            cursor.execute("UPDATE popis_nasljednika SET odrekao_se = FALSE, u_korist_id = NULL WHERE id = %s", (osoba_id,))
                            conn.commit()
                            st.success("Osoba uspješno vraćena u aktivne članove!")
                            st.rerun()
                            
                    if st.button("🗑️ Trajno izbriši osobu iz šifrarnika", key="btn_adm_trajno_del", width="stretch"):
                        cursor.execute("DELETE FROM popis_nasljednika WHERE id = %s", (osoba_id,))
                        conn.commit()
                        st.success("Osoba trajno uklonjena iz baze podataka!")
                        st.rerun()



        # 1. UPIT ZA ODVJETNIKA - DODANA C.ZONA NA KRAJ SELECTA
        p_bodovi = 0


        cursor.execute("""
            SELECT dc.id_cestice, c.broj_cestice, c.zk_ulozak, p.naziv_podrucja, c.povrsina, dc.nasljednik, dc.status_diobe, c.zona, dc.korekcija_postotak,  (c.povrsina * COALESCE(sz.koeficijent_vrijednosti, 1.0)) as pocetni_bodovi
            FROM dioba_cestica dc
            JOIN cestice c ON dc.id_cestice = c.id
            JOIN podrucja p ON c.id_podrucja = p.id
            LEFT JOIN sifrarnik_zona sz ON c.zona = sz.oznaka_zone           
            WHERE dc.oznacena = TRUE
            ORDER BY c.broj_cestice
        """)
        poklikane_cestice = cursor.fetchall()


    

        if poklikane_cestice:
            podaci_za_odvjetnika = []        
            for cid, broj, zk, podrucje, povrsina, nasljednik, status, zon, kor_postotak, p_bodovi in poklikane_cestice: 
    
                podaci_za_odvjetnika.append({
                    "ID Čestice": cid,
                    "Broj čestice": broj,
                    "Zona": zon if zon else "-",  # Novo polje za odvjetnika
                    "ZK Uložak": str(zk) if zk else "-",
                    "Područje": podrucje,
                    "Površina (m²)": float(povrsina) if povrsina else 0.0,
                    "Početni bodovi": int(p_bodovi) if p_bodovi else 0,
                    "Kome pripada (Nasljednik)": nasljednik if nasljednik else "",
                    "Status": status if status else "Interes",
                    "Korekcija vrijednosti (%)": float(kor_postotak) if kor_postotak is not None else 0.0,
                    

                })

                               
            
            df_odvjetnik = pd.DataFrame(podaci_za_odvjetnika)
            trenutni_iz_baze = df_odvjetnik["Kome pripada (Nasljednik)"].dropna().unique()
            popis_s_opcijom = ["", "👥 SUVLASNIŠTVO (Više osoba)"] + list(popis_nasljednika)
            
            for stavka in trenutni_iz_baze:
                if stavka not in popis_s_opcijom and str(stavka).strip() != "":
                    popis_s_opcijom.append(stavka)

            uredjeni_df_odvjetnik = st.data_editor(
                df_odvjetnik,
                hide_index=True,
                disabled=["ID Čestice", "Broj čestice", "Zona", "ZK Uložak", "Područje", "Površina (m²)", "Početni bodovi"],
                width="stretch",
                column_config={
                    "Kome pripada (Nasljednik)": st.column_config.SelectboxColumn("Kome pripada (Nasljednik)", options=popis_s_opcijom, default=""),
                    "Status": st.column_config.SelectboxColumn("Status", options=["Interes", "Dodijeljeno"], default="Interes"),
                    # 2. KORAK: Konfiguriramo stupac kao brojčano polje koje se može uređivati
                    "Korekcija vrijednosti (%)": st.column_config.NumberColumn(
                    "Korekcija vrijednosti (%)", 
                help="Upišite postotak u plusu (npr. 10) ili minusu (npr. -15) za prilagodbu vrijednosti",
                format="%f", 
                step=1.0
                ),
                },
                key="editor_odvjetnika"
            )





            # =========================================================================
            # 📊  LIVE ANALITIKA U  TABOVIMA 
            # =========================================================================
            ukupna_m2_odvjetnik = df_odvjetnik["Površina (m²)"].sum() if not df_odvjetnik.empty else 0.0
            uk_broj_cestica = len(df_odvjetnik) if not df_odvjetnik.empty else 0
            
            # Razvrstavanje po statusima direktno iz DataFrame-a
            df_interes = df_odvjetnik[df_odvjetnik["Status"] == "Interes"] if not df_odvjetnik.empty else pd.DataFrame()
            df_dodijeljeno = df_odvjetnik[df_odvjetnik["Status"] == "Dodijeljeno"] if not df_odvjetnik.empty else pd.DataFrame()
            
            m2_interes = df_interes["Površina (m²)"].sum() if not df_interes.empty else 0.0
            broj_interes = len(df_interes)
            
            m2_dodijeljeno = df_dodijeljeno["Površina (m²)"].sum() if not df_dodijeljeno.empty else 0.0
            broj_dodijeljeno = len(df_dodijeljeno)

            st.write("")
            
            # Stvaramo 2 elegantna taba za razvrstavanje informacija
            tab_analitika1, tab_analitika2 = st.tabs(["📊 Ukupno stanje", "⏳ Stanje po statusu"])
            
            with tab_analitika1:
                # Decentan prikaz s manjim slovima preko HTML-a
                st.markdown(f"""
                <div style="padding: 5px 0px;">
                    <span style="font-size: 0.95rem; color: #555555;">📋 Ukupan broj odabranih čestica:</span> 
                    <strong style="font-size: 1.05rem;">{uk_broj_cestica} </strong>
                    <br>
                    <span style="font-size: 0.95rem; color: #555555;">📐 Ukupna površina odabranih čestica:</span> 
                    <strong style="font-size: 1.05rem;">{int(ukupna_m2_odvjetnik):,}` m²</strong>
                </div>
                """.replace(",", " "), unsafe_allow_html=True)
                
            with tab_analitika2:
                st.markdown(f"""
                <div style="padding: 5px 0px;">
                    <span style="font-size: 0.95rem; color: #555555;">⏳ Preostalo u statusu <b>Interes</b>:</span> 
                    <strong style="font-size: 1.05rem; color: #ff9800;">{broj_interes} </strong> 
                    <span style="font-size: 0.9rem; color: #777777;">({int(m2_interes):,}` m²)</span>
                    <br>
                    <span style="font-size: 0.95rem; color: #555555;">🔒 Uspješno <b>Dodijeljeno</b> nasljednicima:</span> 
                    <strong style="font-size: 1.05rem; color: #4caf50;">{broj_dodijeljeno} </strong> 
                    <span style="font-size: 0.9rem; color: #777777;">({int(m2_dodijeljeno):,}` m²)</span>
                </div>
                """.replace(",", " "), unsafe_allow_html=True)
                
            st.write("")




                        # =========================================================================
            # 📊 ČISTI DINAMIČKI POPIS ZONA IZ BAZE PODATAKA (Učitava se prije spremanja)
            # =========================================================================
            try:
                cursor.execute("SELECT oznaka_zone, koeficijent_vrijednosti FROM public.sifrarnik_zona WHERE oznaka_zone != '-' ORDER BY oznaka_zone")
                sve_zone_baza = cursor.fetchall()
                conn.commit() # Odmah oslobađamo transakciju čitanja da baza ostane brza
                
                # Sastavljamo živu listu bez ijedne fiksne riječi u kodu
                stavke_sifrarnika = [f"**{zona}** ({float(koef):.2f})" for zona, koef in sve_zone_baza]
                popis_zona_tekst = ", ".join(stavke_sifrarnika)
            except Exception:
                try: conn.rollback()
                except Exception: pass
                popis_zona_tekst = "Učitavanje..."

            # 3. KORAK: Nadopuna petlje za spremanje svih promjena odjednom (0% kvačica)
            izmjene = st.session_state.get("editor_odvjetnika", {}).get("edited_rows", {})
            
            
            
            if izmjene:
                promjene_odvjetnika = 0
                for indeks_retka, promijenjena_polja in izmjene.items():
                    # 1. Čitamo izvorne podatke iz tablice za ovaj redak
                    stari_nasljednik = df_odvjetnik.iloc[int(indeks_retka)]["Kome pripada (Nasljednik)"]
                    stari_status = df_odvjetnik.iloc[int(indeks_retka)]["Status"]
                    stara_korekcija = float(df_odvjetnik.iloc[int(indeks_retka)].get("Korekcija vrijednosti (%)", 0.0))
                    
                    cid = int(df_odvjetnik.iloc[int(indeks_retka)]["ID Čestice"])
                    broj = str(df_odvjetnik.iloc[int(indeks_retka)]["Broj čestice"])

                    # 2. Izvlačimo nove vrijednosti ako ih je odvjetnik upisao
                    novi_nasljednik = promijenjena_polja.get("Kome pripada (Nasljednik)", stari_nasljednik)
                    novi_status = promijenjena_polja.get("Status", stari_status)
                    
                    nova_korekcija_sirovo = promijenjena_polja.get("Korekcija vrijednosti (%)", stara_korekcija)
                    nova_korekcija = float(nova_korekcija_sirovo) if nova_korekcija_sirovo is not None else 0.0

                    # 3. SLUČAJ A: Korisnik je odabrao opciju SUVLASNIŠTVO više osoba
                    if novi_nasljednik == "👥 SUVLASNIŠTVO (Više osoba)":
                        st.write("---")
                        st.markdown(f"### 👥 Odaberite suvlasnike iz baze za česticu **{broj}**")
                        
                        # Čisti izbornik s kvačicama koji vuče ljude direktno iz vaše baze
                        odabrani_suvlasnici = st.multiselect(
                            "Klikom označite nasljednike (bez utipkavanja):",
                            options=popis_nasljednika,
                            key=f"multi_suv_{cid}"
                        )
                        
                        if st.button("💾 Spremi suvlasnike", key=f"btn_suv_{cid}", type="primary"):
                            imena_skupa = ", ".join(odabrani_suvlasnici) if odabrani_suvlasnici else ""
                            cursor.execute(
                                "UPDATE dioba_cestica SET nasljednik = %s, status_diobe = 'Dodijeljeno', korekcija_postotak = %s WHERE id_cestice = %s",
                                (imena_skupa, nova_korekcija, cid)
                            )
                            conn.commit()
                            st.success(f"Uspješno spremljeno suvlasništvo: {imena_skupa}")
                            st.rerun()
                    
                    # 4. SLUČAJ B: Korisnik radi običnu dodjelu pojedinačnom nasljedniku
                    else:
                        # Automatska prilagodba statusa ovisno o upisu
                        if not novi_nasljednik or str(novi_nasljednik).strip() == "" or novi_status == "Interes":
                            novi_nasljednik = ""
                            novi_status = "Interes"
                        elif novi_nasljednik:
                            novi_status = "Dodijeljeno"

                        # Ako se bilo koje od ova 3 polja razlikuje, radimo UPDATE u bazu
                        if novi_nasljednik != stari_nasljednik or novi_status != stari_status or nova_korekcija != stara_korekcija:
                            vrijednost_baza = novi_nasljednik if novi_nasljednik != "" else None
                            
                            # Ažuriramo stanje diobe i novi korekcijski postotak u bazi
                            cursor.execute(
                                "UPDATE dioba_cestica SET nasljednik = %s, status_diobe = %s, korekcija_postotak = %s WHERE id_cestice = %s", 
                                (vrijednost_baza, novi_status, nova_korekcija, cid)
                            )
                            
                            # Upisujemo u log
                            akcija_log = f"DODIJELJENO ({novi_nasljednik}) [Kor: {nova_korekcija}%]" if novi_nasljednik != "" else "RESETIRANO"
                            cursor.execute("INSERT INTO log_diobe_cestica (id_cestice, broj_cestice, akcija, ip_adresa) VALUES (%s, %s, %s, %s)", (cid, broj, akcija_log, ip_adresa))
                            promjene_odvjetnika += 1



            if st.button("⚖️ Spremi konačnu raspodjelu", key="btn_save_odvjetnik", width="stretch"):
#####
                odabrani_nasljednici = uredjeni_df_odvjetnik["Kome pripada (Nasljednik)"].dropna().astype(str).str.strip().values
        
                if "👥 SUVLASNIŠTVO (Više osoba)" in odabrani_nasljednici:
                    st.error("⚠️ Nemoguće spremiti! Na nekim česticama je odabrano 'SUVLASNIŠTVO', ali niste definirali konkretne osobe u skočnom prozoru.")
                    st.stop()  # Zaustavlja daljnje izvršavanje koda (blokira petlju ispod)
#####
                promjene_odvjetnika = 0
                for indeks_red, redak in uredjeni_df_odvjetnik.iterrows():
                    cid = int(redak["ID Čestice"])
                    broj = str(redak["Broj čestice"])
                    
                    # 🛠️ 1. SIGURNOSNI FILTER: Izvlačimo sirovi tekst i uništavamo Pandas 'nan' oblike
                    novi_nasljednik_sirovo = str(redak["Kome pripada (Nasljednik)"]).strip()
                    novi_status_sirovo = str(redak["Status"]).strip()

                    # Ako je ćelija ispražnjena ili doslovno piše 'nan' / 'None', čistimo je na prazan string
                    if not novi_nasljednik_sirovo or novi_nasljednik_sirovo.lower() in ["nan", "none", "null", ""]:
                        novi_nasljednik = ""
                    else:
                        novi_nasljednik = novi_nasljednik_sirovo

                    # Ako je status obrisan, automatski ga vraćamo na početni 'Interes'
                    if not novi_status_sirovo or novi_status_sirovo.lower() in ["nan", "none", "null", ""]:
                        novi_status = "Interes"
                    else:
                        novi_status = novi_status_sirovo

                    # Dohvaćamo staro stanje radi usporedbe
                    stara_stavka = [x for x in poklikane_cestice if x[0] == cid]
                    if stara_stavka:
                        stari_nasljednik = stara_stavka[0][5] if stara_stavka[0][5] else ""
                        stari_status = stara_stavka[0][6] if stara_stavka[0][6] else "Interes"
                    else:
                        stari_nasljednik = ""
                        stari_status = "Interes"

                    # 🛠️ 2. USPOREDBA I SIGURAN UPIS (U bazu ide čisti SQL NULL ako nema nasljednika)
                    if novi_nasljednik != stari_nasljednik or novi_status != stari_status:
                        vrijednost_baza = novi_nasljednik if novi_nasljednik != "" else None
                        
                        # 1. Ažuriramo trenutno stanje diobe u bazi podataka
                        cursor.execute("UPDATE dioba_cestica SET nasljednik = %s, status_diobe = %s WHERE id_cestice = %s", (vrijednost_baza, novi_status, cid))
                        
                        # 2. Upisujemo u log dugački tekst (Ako je nasljednik ispražnjen, log bilježi RESETIRANO)
                        akcija_log = f"DODIJELJENO ({novi_nasljednik})" if novi_nasljednik != "" else "RESETIRANO"
                        cursor.execute("INSERT INTO log_diobe_cestica (id_cestice, broj_cestice, akcija, ip_adresa) VALUES (%s, %s, %s, %s)", (cid, broj, akcija_log, ip_adresa))
                        promjene_odvjetnika += 1

                if promjene_odvjetnika > 0:

                    # =========================================================================
                    #  dohvat bodova iz baze
                    # =========================================================================
                    try:
                        import json
                       # cursor.execute("TRUNCATE TABLE public.live_statistika_diobe RESTART IDENTITY CASCADE;")
                        cursor.execute("DELETE FROM public.live_statistika_diobe;")
                        conn.commit()


                        df_live = uredjeni_df_odvjetnik.copy()
                        
                        c_povrsina = "Površina (m²)" if "Površina (m²)" in df_live.columns else "Površina (m2)"
                        c_bodovi = "Bodovi" if "Bodovi" in df_live.columns else "Vrijednost (bodovi)"
                        c_korekcija = "Korekcija vrijednosti (%)" if "Korekcija vrijednosti (%)" in df_live.columns else "Korekcija vrijednosti"
                        c_nasljednik = "Kome pripada (Nasljednik)"
                        c_status = "Status"

                        # 💎 Formula je čisti zbroj: Osnovni bodovi + Korekcija
                        # Ako je osnovni broj bodova 2152, a korekcija -1000, rezultat je 1152!
                        df_live["Vrijednosni bodovi"] = df_live[c_bodovi].fillna(0).astype(float) + df_live[c_korekcija].fillna(0).astype(float)

                        uk_komada = len(df_live) if len(df_live) > 0 else 1
                        rijeseno_komada = len(df_live[df_live[c_status] != "Interes"])
                        postotak_rjesenja = (rijeseno_komada / uk_komada) * 100
                        preostalo_cestica = len(df_live[df_live[c_status] == "Interes"])

                        df_live_dodijeljeno = df_live[
                            (df_live[c_status] == "Dodijeljeno") & 
                            (df_live[c_nasljednik].notna()) &
                            (df_live[c_nasljednik].astype(str).str.strip() != "")
                        ]

                        razbijeni_podaci = []
                        for _, red in df_live_dodijeljeno.iterrows():
                            nasl_tekst = red[c_nasljednik]
                            povrsina = float(red.get(c_povrsina, 0))
                            bodovi = float(red.get("Vrijednosni bodovi", 0))
                            svi_nasljednici = [n.strip() for n in str(nasl_tekst).split(",") if n.strip()]
                            broj_suvlasnika = len(svi_nasljednici)
                            
                            if broj_suvlasnika > 0:
                                for ime in svi_nasljednici:
                                    razbijeni_podaci.append({
                                        "Nasljednik": ime,
                                        "Povrsina": povrsina / broj_suvlasnika,
                                        "Bodovi": bodovi / broj_suvlasnika
                                    })

                        if razbijeni_podaci:
                            df_razbijeno = pd.DataFrame(razbijeni_podaci)
                            statistika_live = df_razbijeno.groupby("Nasljednik").agg({
                                "Povrsina": "sum",
                                "Bodovi": "sum"
                            }).reset_index()
                            
                            ukupno_m2_live = statistika_live["Povrsina"].sum()
                            ukupno_bodova_live = statistika_live["Bodovi"].sum()
                            statistika_live["Udio"] = (statistika_live["Bodovi"] / ukupno_bodova_live * 100).round(2) if ukupno_bodova_live > 0 else 0.0
                            json_nasljednici = statistika_live.to_json(orient="records")
                        else:
                            ukupno_m2_live, ukupno_bodova_live = 0.0, 0.0
                            json_nasljednici = json.dumps([])

                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS public.live_statistika_diobe (
                                id int PRIMARY KEY,
                                postotak numeric,
                                bodovi numeric,
                                povrsina numeric,
                                preostalo int,
                                tablica_nasljednika text
                            );
                        """)

                        cursor.execute("""
                            INSERT INTO public.live_statistika_diobe (id, postotak, bodovi, povrsina, preostalo, tablica_nasljednika)
                            VALUES (1, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET 
                                postotak = EXCLUDED.postotak,
                                bodovi = EXCLUDED.bodovi,
                                povrsina = EXCLUDED.povrsina,
                                preostalo = EXCLUDED.preostalo,
                                tablica_nasljednika = EXCLUDED.tablica_nasljednika;
                        """, (float(postotak_rjesenja), float(ukupno_bodova_live), float(ukupno_m2_live), int(preostalo_cestica), json_nasljednici))
                        
                    except Exception as e:
                        st.sidebar.error(f"Usporenje sinkronizacije izbjegnuto: {e}")

                    conn.commit()
                    st.success(f"⚖️ Raspodjela uspješno spremljena!")
                    st.rerun()
                else:
                    st.info("Nema novih izmjena u raspodjeli za spremiti.")


            # =========================================================================
            # 📊 UNIVERZALNI SUSTAV PREKO ŠIFRARNIKA ZONA 
            # =========================================================================
            st.write("---")
            st.markdown("### 📊 Kontrola pravednosti raspodjele")
            st.write("Sustav računa stvarnu površinu i vrijednosne bodove na temelju koeficijenata zona.")

            # 1. Povlačimo sve zone i koeficijente uživo iz baze podataka (Nema try-except skrivača)
            cursor.execute("SELECT oznaka_zone, koeficijent_vrijednosti FROM sifrarnik_zona")
            koeficijenti_baza = {str(zona).strip().upper(): float(koef) for zona, koef in cursor.fetchall()}

            
            df_dodijeljeno = uredjeni_df_odvjetnik[
                (uredjeni_df_odvjetnik["Status"] == "Dodijeljeno") & 
                (uredjeni_df_odvjetnik["Kome pripada (Nasljednik)"].notna()) &
                (uredjeni_df_odvjetnik["Kome pripada (Nasljednik)"].str.strip() != "")
            ].copy()

            
            cursor.execute("TRUNCATE TABLE public.live_statistika_diobe RESTART IDENTITY CASCADE;")
            conn.commit()

            if not df_dodijeljeno.empty:
                def dohvati_koef_iz_baze(zona_tekst):
                    sigurnosni_default = koeficijenti_baza.get("-", 1.00)
                    
                    if not zona_tekst or str(zona_tekst).strip() == "" or str(zona_tekst).strip() == "-":
                        return sigurnosni_default
                        
                    zona_cista = str(zona_tekst).strip().upper()
                    if zona_cista in koeficijenti_baza:
                        return koeficijenti_baza[zona_cista]
                        
                    # KORAK B: Rastavljanje kombinacije na pojedinačne zone
                    pojedinacne_zone = [z.strip() for z in zona_cista.replace("/", " ").replace("-", " ").split() if z.strip() != ""]
                    pronadjeni_koeficijenti = []
                    
                    for kljuc_baza, koef_vrijednost in koeficijenti_baza.items():
                        for p_zona in pojedinacne_zone:
                            if p_zona == kljuc_baza or kljuc_baza in p_zona:
                                pronadjeni_koeficijenti.append(koef_vrijednost)
                    if pronadjeni_koeficijenti:
                        return max(pronadjeni_koeficijenti)
                        
                    return sigurnosni_default
                df_dodijeljeno["Faktor Korekcije"] = 1.0 + (df_dodijeljeno["Korekcija vrijednosti (%)"] / 100.0)
                
                df_dodijeljeno["Koeficijent"] = df_dodijeljeno["Zona"].apply(dohvati_koef_iz_baze)
                
                # Formula uzima osnovne bodove i na njih samo zbraja/oduzima upisani iznos
                df_dodijeljeno["Vrijednosni bodovi"] = (df_dodijeljeno["Površina (m²)"] * df_dodijeljeno["Koeficijent"]) + df_dodijeljeno["Korekcija vrijednosti (%)"].fillna(0).astype(float)



                razbijeni_podaci = []
                
                for _, red in df_dodijeljeno.iterrows():
                    nasl_tekst = red["Kome pripada (Nasljednik)"]
                    povrsina = float(red.get("Površina (m²)", 0))
                    bodovi = float(red.get("Vrijednosni bodovi", 0))
                    svi_nasljednici = [n.strip() for n in str(nasl_tekst).split(",") if n.strip()]
                    broj_suvlasnika = len(svi_nasljednici)
                    
                    if broj_suvlasnika > 0:
                        povrsina_po_osobi = povrsina / broj_suvlasnika
                        bodovi_po_osobi = bodovi / broj_suvlasnika
                        for ime in svi_nasljednici:
                            razbijeni_podaci.append({
                                "Kome pripada (Nasljednik)": ime,
                                "Površina (m²)": povrsina_po_osobi,
                                "Vrijednosni bodovi": bodovi_po_osobi
                            })

               # cursor.execute("TRUNCATE TABLE public.live_statistika_diobe RESTART IDENTITY CASCADE;")

                if razbijeni_podaci:
                    df_razbijeno = pd.DataFrame(razbijeni_podaci)
                    statistika = df_razbijeno.groupby("Kome pripada (Nasljednik)").agg({
                        "Površina (m²)": "sum",
                        "Vrijednosni bodovi": "sum"
                    }).reset_index()
                else:
                    statistika = pd.DataFrame(columns=["Kome pripada (Nasljednik)", "Površina (m²)", "Vrijednosni bodovi"])

                ukupno_m2 = statistika["Površina (m²)"].sum()
                ukupno_bodova = statistika["Vrijednosni bodovi"].sum()
                if ukupno_bodova > 0:
                    statistika["Udio u vrijednosti imanja"] = (statistika["Vrijednosni bodovi"] / ukupno_bodova * 100).round(2)
                else:
                    statistika["Udio u vrijednosti imanja"] = 0.0

                sirovi_zbroj_posto = statistika["Udio u vrijednosti imanja"].sum()
                if 99.5 <= sirovi_zbroj_posto <= 100.5:
                    ukupno_posto = 100.00
                else:
                    ukupno_posto = round(sirovi_zbroj_posto, 2)

                statistika["Ukupna stvarna površina"] = statistika["Površina (m²)"].apply(lambda x: f"{int(x):,} m²".replace(",", " "))
                statistika["Procijenjena vrijednost (Bodovi)"] = statistika["Vrijednosni bodovi"].apply(lambda x: f"{int(x):,}".replace(",", " ")) # 🔥 Popravljen krivi format specifier
                statistika["Udio u vrijednosti imanja (%)"] = statistika["Udio u vrijednosti imanja"].apply(lambda x: f"{x:.2f} %")

                tablica_prikaz = statistika[[
                    "Kome pripada (Nasljednik)", 
                    "Ukupna stvarna površina", 
                    "Procijenjena vrijednost (Bodovi)", 
                    "Udio u vrijednosti imanja (%)"
                ]]
                tablica_prikaz.columns = ["Nasljednik / Obiteljska grana", "Ukupna stvarna površina", "Procijenjena vrijednost (Bodovi)", "Udio u vrijednosti imanja (%)"]

                red_ukupno = pd.DataFrame([{
                    "Nasljednik / Obiteljska grana": "═══ 🛑 UKUPNO PODIJELJENO ═══",
                    "Ukupna stvarna površina": f"📊 {int(ukupno_m2):,} m²".replace(",", " "),
                    "Procijenjena vrijednost (Bodovi)": f"💎 {int(ukupno_bodova):,}".replace(",", " "),
                    "Udio u vrijednosti imanja (%)": f"🎯 {ukupno_posto:.2f} %"
                }])

                konacni_df_prikaz = pd.concat([tablica_prikaz, red_ukupno], ignore_index=True)
                st.dataframe(
                    konacni_df_prikaz, 
                    hide_index=True, 
                    width="stretch",
                    column_config={
                        "Ukupna stvarna površina": st.column_config.Column("Ukupna stvarna površina", alignment="right"),
                        "Procijenjena vrijednost (Bodovi)": st.column_config.Column("Procijenjena vrijednost (Bodovi)", alignment="right"),
                        "Udio u vrijednosti imanja (%)": st.column_config.Column("Udio u vrijednosti imanja (%)", alignment="right")
                    }
                )

              

                # =========================================================================
                # 📊 SINKRONIZACIJA: Slanje Vaših stopostotno točnih brojki na mobitele
                # =========================================================================
                try:
                    import json

                    # Računamo točan postotak riješenosti: koliko čestica NIJE u statusu 'Interes'
                    uk_komada = len(uredjeni_df_odvjetnik) if len(uredjeni_df_odvjetnik) > 0 else 1
                    rijeseno_komada = len(uredjeni_df_odvjetnik[uredjeni_df_odvjetnik["Status"] != "Interes"])
                    postotak_rjesenja = (rijeseno_komada / uk_komada) * 100
                    preostalo_cestica = len(uredjeni_df_odvjetnik[uredjeni_df_odvjetnik["Status"] == "Interes"])

                    # Pakiramo Vašu 'statistika' tablicu s točnim imenima i postocima od 100%
                    podaci_lista = []
                    for _, red_s in statistika.iterrows():
                        podaci_lista.append({
                            "Nasljednik": str(red_s["Kome pripada (Nasljednik)"]),
                            "Povrsina": float(red_s["Površina (m²)"]),
                            "Bodovi": float(red_s["Vrijednosni bodovi"]),
                            "Udio": float(red_s["Udio u vrijednosti imanja"])
                        })

                    json_nasljednici = json.dumps(podaci_lista)

                    # Osiguravamo samo postojanje tablice za mobitele na cloudu
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS public.live_statistika_diobe (
                            id int PRIMARY KEY,
                            postotak numeric,
                            bodovi numeric,
                            povrsina numeric,
                            preostalo int,
                            tablica_nasljednika text
                        );
                    """)

            #         # Upisujemo Vaše gotove, preračunate brojke u bazu
            #         cursor.execute("""
            #             INSERT INTO public.live_statistika_diobe (id, postotak, bodovi, povrsina, preostalo, tablica_nasljednika)
            #             VALUES (1, %s, %s, %s, %s, %s)
            #             ON CONFLICT (id) DO UPDATE SET 
            #                 postotak = EXCLUDED.postotak,
            #                 bodovi = EXCLUDED.bodovi,
            #                 povrsina = EXCLUDED.povrsina,
            #                 preostalo = EXCLUDED.preostalo,
            #                 tablica_nasljednika = EXCLUDED.tablica_nasljednika;
            #         """, (float(postotak_rjesenja), float(ukupno_bodova), float(ukupno_m2), int(preostalo_cestica), json_nasljednici))
            #         conn.commit()

            #     except Exception as e:
            #         st.sidebar.error(f"Pomoćni mobilni sinkronizator: {e}")

                
            #     st.caption(f"💡 *Napomena: Vrijednosni bodovi računaju se množenjem površine s koeficijentom zone iz šifrarnika koji se trenutno primjenjuje za ovaj obračun: {popis_zona_tekst}. Kod čestica koje se protežu kroz više zona (kombinirane zone), sustav automatski prepoznaje sve navedene zone, ali obračun bodova temelji na koeficijentu najvrjednije priznate zone u toj kombinaciji. Time se vrijednost preostalih, manje vrijednih dijelova čestice u konačnom izračunu smanjuje u korist dominantne ekonomske cjeline.*")
            # else:
            #     st.caption("U gornjoj tablici promijenite status barem jedne čestice u 'Dodijeljeno' i odaberite nasljednika kako bi se pokrenuo automatski izračun pravednosti.")

                    # Upisujemo Vaše gotove, preračunate brojke u bazu
                    cursor.execute("""
                        INSERT INTO public.live_statistika_diobe (id, postotak, bodovi, povrsina, preostalo, tablica_nasljednika)
                        VALUES (1, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET 
                            postotak = EXCLUDED.postotak,
                            bodovi = EXCLUDED.bodovi,
                            povrsina = EXCLUDED.povrsina,
                            preostalo = EXCLUDED.preostalo,
                            tablica_nasljednika = EXCLUDED.tablica_nasljednika;
                    """, (float(postotak_rjesenja), float(ukupno_bodova), float(ukupno_m2), int(preostalo_cestica), json_nasljednici))
                    conn.commit()

                except Exception as e:
                    st.sidebar.error(f"Pomoćni mobilni sinkronizator: {e}")
                
                st.caption(f"💡 *Napomena: Vrijednosni bodovi računaju se množenjem površine...*")
            
            else:
                # 🛠️ KLJUČNI POPRAVAK: Kada nema više niti jedne dodjele, aplikacija upada ovdje.
                # Šaljemo eksplicitni DELETE i COMMIT kako bi id=1 trajno nestao iz baze!
                try:
                    cursor.execute("DELETE FROM public.live_statistika_diobe WHERE id = 1;")
                    conn.commit()
                except Exception:
                    pass

                st.caption("U gornjoj tablici promijenite status barem jedne čestice u 'Dodijeljeno' i odaberite nasljednika kako bi se pokrenuo automatski izračun pravednosti.")
