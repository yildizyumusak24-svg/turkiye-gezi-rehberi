import streamlit as st
import requests

STRAPI_URL = "http://localhost:1337"

st.set_page_config(page_title="Turkiye Gezi Rehberi", page_icon="🗺️", layout="wide")

st.markdown("""
<style>
.puan-badge {
    background: #e74c3c; color: white;
    padding: 4px 10px; border-radius: 20px;
    font-weight: bold; font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def sehirleri_getir():
    url = f"{STRAPI_URL}/api/sehirs?populate=kapak_resmi"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json().get("data", [])

@st.cache_data(ttl=60)
def mekanlari_getir(sehir_id):
    url = (
        f"{STRAPI_URL}/api/mekans"
        f"?filters[sehir][id][$eq]={sehir_id}"
        f"&populate=gorsel"
        f"&sort=puan:desc"
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json().get("data", [])

def gorsel_url_al(mekan):
    try:
        # Strapi 5 format
        g = mekan.get("gorsel") or mekan.get("attributes", {}).get("gorsel", {})
        if isinstance(g, dict):
            data = g.get("data") or g
            if isinstance(data, dict):
                url = data.get("url") or data.get("attributes", {}).get("url")
                if url:
                    return STRAPI_URL + url
    except Exception:
        pass
    return None

def alan_al(obj, alan):
    """Strapi 4 (attributes) ve Strapi 5 (flat) formatlarini destekler."""
    if "attributes" in obj:
        return obj["attributes"].get(alan)
    return obj.get(alan)

# Ana arayuz
st.markdown("# 🗺️ Turkiye Gezi Rehberi")
st.markdown("*YZ destekli dinamik seyahat icerikleri*")
st.divider()

try:
    sehirler = sehirleri_getir()
except Exception as e:
    st.error(f"Strapi'ye baglanılamadı: {e}")
    st.info("Strapi'nin calistigından emin olun: http://localhost:1337")
    st.stop()

if not sehirler:
    st.warning("Henuz sehir kaydi yok. Once otomasyon.py dosyasini calistirin.")
    st.stop()

dil = st.radio("Dil / Language:", ["Turkce", "English"], horizontal=True)

sehir_adlari = {s["id"]: alan_al(s, "ad") for s in sehirler}
secilen_id = st.selectbox("Sehir secin:", options=list(sehir_adlari.keys()), format_func=lambda x: sehir_adlari[x])

st.divider()

secilen_sehir = next(s for s in sehirler if s["id"] == secilen_id)
col1, col2 = st.columns([2, 1])
with col1:
    st.markdown(f"## {alan_al(secilen_sehir, 'ad')}")
    st.markdown(f"**Ulke:** {alan_al(secilen_sehir, 'ulke') or 'Turkiye'}")

with st.spinner("Mekanlar yukleniyor..."):
    try:
        mekanlar = mekanlari_getir(secilen_id)
    except Exception as e:
        st.error(f"Mekanlar alinamadi: {e}")
        st.stop()

with col2:
    st.metric("Toplam Mekan", len(mekanlar))

if not mekanlar:
    st.info("Bu sehire ait mekan bulunamadi.")
    st.stop()

st.markdown(f"### Kesfedilecek Mekanlar ({len(mekanlar)} mekan)")

for mekan in mekanlar:
    puan = alan_al(mekan, "puan") or 0
    ad   = alan_al(mekan, "ad") or "?"
    gorsel = gorsel_url_al(mekan)

    with st.container():
        img_col, bilgi_col = st.columns([1, 2])
        with img_col:
            if gorsel:
                st.image(gorsel, use_container_width=True, caption=ad)
            else:
                st.image("https://picsum.photos/400/300", use_container_width=True)
        with bilgi_col:
            st.markdown(f"### {ad}")
            st.markdown(f'<span class="puan-badge">⭐ {puan}/10</span>', unsafe_allow_html=True)
            st.markdown("")
            if dil == "Turkce":
                blocks = alan_al(mekan, "aciklama") or []
                if blocks:
                    metin = " ".join(
                        child.get("text", "")
                        for block in blocks
                        for child in block.get("children", [])
                    )
                    st.markdown(metin)
                else:
                    st.markdown("*Aciklama mevcut degil.*")
            else:
                en = alan_al(mekan, "yz_aciklama") or ""
                st.markdown(en if en else "*Description not available.*")
        st.divider()

st.markdown("---")
st.markdown("<center><small>BIP210 Final Projesi • YZ Destekli Gezi Rehberi</small></center>", unsafe_allow_html=True)
