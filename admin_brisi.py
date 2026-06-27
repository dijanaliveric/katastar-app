import psycopg2
import streamlit as st


def prikazi_brisanje(conn, cursor, c_glavni_dict):
    st.subheader("❌ Trajno brisanje zapisa iz arhive")
    col_bris1, col_bris2 = st.columns(2)

    with col_bris1:
        st.markdown("### 🗺️ Brisanje Čestice")
        if c_glavni_dict:
            za_brisanje_c = st.selectbox(
                "Odaberi česticu:", list(c_glavni_dict.keys()), key="bris_c"
            )
            potvrda_c = st.checkbox(
                f"Potvrđujem brisanje čestice {za_brisanje_c}"
            )
            if st.button("🔥 Trajno obriši česticu", disabled=not potvrda_c):
                id_bris_c = c_glavni_dict[za_brisanje_c]
                cursor.execute(
                    "DELETE FROM povijest_dokumenata WHERE id_cestice = ?",
                    (id_bris_c,),
                )
                cursor.execute(
                    "DELETE FROM cestice WHERE id = ?", (id_bris_c,)
                )
                conn.commit()
                st.success("Čestica i njezini dokumenti su obrisani.")
                st.rerun()
        else:
            st.info("Nema čestica u bazi.")

    with col_bris2:
        st.markdown("### 📄 Brisanje Pojedinačnog Lista")
        cursor.execute("SELECT id, vrsta_lista, broj_lista_korisnika, (SELECT broj_cestice FROM cestice WHERE id=id_cestice) FROM povijest_dokumenata")
        svi_d = cursor.fetchall()
        
        if svi_d:
            d_dict = {
                f"{vrsta} br. {broj} (na čestici {c_broj})": i
                for i, vrsta, broj, c_broj in svi_d
            }
            za_brisanje_d = st.selectbox(
                "Odaberi list:", list(d_dict.keys()), key="bris_d"
            )

            potvrda_d = st.checkbox("Potvrđujem brisanje ovog dokumenta")
            if st.button("🔥 Trajno obriši dokument", disabled=not potvrda_d):
                cursor.execute(
                    "DELETE FROM povijest_dokumenata WHERE id = ?",
                    (d_dict[za_brisanje_d],),
                )
                conn.commit()
                st.success("Dokument je obrisan.")
                st.rerun()
        else:
            st.info("Nema povijesnih listova u bazi.")
