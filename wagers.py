from bs4 import BeautifulSoup
from datetime import datetime
import numpy as np
import pandas as pd
import requests
import scipy.stats as stats
import streamlit as st

sport_details = {
    "NCAAB": {
        "url": {
            "schedule": "https://www.teamrankings.com/ncb/schedules/",
            "off_eff": "https://www.teamrankings.com/ncaa-basketball/stat/offensive-efficiency",
            "def_eff": "https://www.teamrankings.com/ncaa-basketball/stat/defensive-efficiency",
            "pos_per_game": "https://www.teamrankings.com/ncaa-basketball/stat/possessions-per-game",
            "home_court_adv": "https://www.teamrankings.com/ncaa-basketball/ranking/home-adv-by-other"
        },
        "std_dev": {
            "total": 14,
            "spread": 11
        }
    },
    "NBA": {
        "url": {
            "schedule": "https://www.teamrankings.com/nba/schedules/",
            "off_eff": "https://www.teamrankings.com/nba/stat/offensive-efficiency",
            "def_eff": "https://www.teamrankings.com/nba/stat/defensive-efficiency",
            "pos_per_game": "https://www.teamrankings.com/nba/stat/possessions-per-game",
            "home_court_adv": "https://www.teamrankings.com/nba/ranking/home-adv-by-other"
        },
        "std_dev": {
            "total": 16,
            "spread": 12
        }
    }
}

today = datetime.today()
formatted_date = f"{today.year}-{today.month:02d}-{today.day:02d}"

time_now = datetime.now()

def adjust_stat(
    avg:float, avg_pct:float, 
    recent_n:float, recent_n_pct:float, 
    last:float, last_pct:float
) -> float:
    
    new_avg = avg * avg_pct/100
    new_recent_n = recent_n * recent_n_pct/100
    new_last = last * last_pct/100

    return new_avg + new_recent_n + new_last

def make_table_score(z_score:float) -> float:
    # z_score = np.abs(z_score)
    table_raw = stats.norm.cdf(z_score)
    table_score = table_raw * 100

    return table_score

def j_projection(
    protag_off_eff:float, antag_def_eff:float, 
    lae:float, projected_tem:float
) -> float:
    projection = (
        (
            (protag_off_eff * 100) 
            *
            (antag_def_eff * 100 / lae)
        ) 
        *
        (projected_tem / 100)
    )

    return projection

def r_projection(
        protag_off_eff:float, antag_def_eff:float,
        lae:float, proj_tem:float
) -> float:
    midpoint = np.mean([protag_off_eff, antag_def_eff])
    projection = (
        (
            (midpoint * 100)
            *
            (midpoint * 100 / lae)
        )
        *
        (proj_tem / 100)
    )

    return projection

# WEIGHTS
avg_weight = 60
last3_weight = 30
last1_weight = 10

website = "https://www.teamrankings.com"

target_sport = st.selectbox(
    label = "Select sport",
    options=["NCAAB", "NBA"]
)

def handle_load_btn():
    URL = f"{sport_details[target_sport]["url"]["schedule"]}?date={formatted_date}"

    response = requests.get(URL)
    games_soup = BeautifulSoup(response.text, "html.parser")
    matches = games_soup.find("tbody").find_all("tr")

    # loading score pages
    off_url = f"{sport_details[target_sport]["url"]["off_eff"]}?date={formatted_date}"
    off_response = requests.get(off_url)
    off_soup =  BeautifulSoup(off_response.text, "html.parser")

    def_url = f"{sport_details[target_sport]["url"]["def_eff"]}?date={formatted_date}"
    def_response = requests.get(def_url)
    def_soup = BeautifulSoup(def_response.text, "html.parser")

    tem_url = f"{sport_details[target_sport]["url"]["pos_per_game"]}?date={formatted_date}"
    tem_response = requests.get(tem_url)
    tem_soup = BeautifulSoup(tem_response.text, "html.parser")

    home_court_adv_url = sport_details[target_sport]["url"]["home_court_adv"]
    home_court_adv_response = requests.get(home_court_adv_url)
    home_court_adv_soup = BeautifulSoup(home_court_adv_response.text, "html.parser")

    off_scores = []
    off_rows = off_soup.find("tbody").find_all("tr")
    for match_row in off_rows:
        tds = match_row.find_all("td")
        score = tds[2]["data-sort"]
        off_scores.append(float(score))

    lao = float(np.mean(off_scores) * 100)

    def_scores = []
    def_rows = def_soup.find("tbody").find_all("tr")
    for match_row in def_rows:
        tds = match_row.find_all("td")
        score = tds[2]["data-sort"]
        def_scores.append(float(score))
    lad = float(np.mean(def_scores) * 100)

    tem_scores = []
    tem_rows = tem_soup.find("tbody").find_all("tr")
    for match_row in tem_rows:
        tds = match_row.find_all("td")
        score = tds[2]["data-sort"]
        tem_scores.append(float(score))
    lat = float(np.mean(tem_scores))

    hca = float(home_court_adv_soup.select("main[role=main] > p")[0].text.split(": ")[1])

    matches_wagers = []
    n_matches = len(matches)

    for match_idx, match_row in enumerate(matches):
        # if match_idx not in [9-1]:
        #     continue
        match_dict = {}
        cells = match_row.find_all("td")
        match = cells[2].find("a")
        match_time_raw = cells[3].text.strip()
        match_time_tgt = datetime.strptime(
            match_time_raw, 
            "%I:%M %p"
        ).replace(
            year = time_now.year,
            month = time_now.month,
            day = time_now.day
        )

        match_link = f"{website}{match['href']}"

        match_response = requests.get(match_link)

        match_soup = BeautifulSoup(match_response.text, "html.parser")

        title = match_soup.find("h1")
        match_dict["name"] = title.text.split(':')[0]

        st.markdown(f"#### :red[MATCH #{match_idx+1}/{n_matches}] ({match_time_raw})")
        st.markdown(f"#### [{title.text.split(':')[0].upper()}]({match_link})")
        
        if match_time_tgt < time_now:
            st.write("Too late to place bet")
            continue

        neutral = None

        if " at " in title.text or "@" in title.text:
            neutral = False
        elif "vs" in title.text:
            neutral = True
        else:
            st.write(f"Couldn't read title: {title.text}")
            continue

        teams = title.find_all("a")

        team_list = []

        for i, team in enumerate(teams):
            team_dict = {
                "name": team.text.strip()
            }

            if not neutral and 1 == i:
                team_dict["home"] = True
            else:
                team_dict["home"] = False

            team_list.append(team_dict)

            team_link = f"{website}{team['href']}"

            team_response = requests.get(team_link)

            team_soup = BeautifulSoup(team_response.text, "html.parser")
            
            team_off_row = off_soup.find("a", href=team_link).parent.parent

            team_off_cells = team_off_row.find_all("td")

            off_avg = float(team_off_cells[2]["data-sort"])
            team_dict["off_avg"] = off_avg

            off_last3 = float(team_off_cells[3]["data-sort"])
            team_dict["off_last3"] = off_last3

            off_last1 = float(team_off_cells[4]["data-sort"])
            team_dict["off_last1"] = off_last1

            off_adj = adjust_stat(
                avg = off_avg, avg_pct = avg_weight,
                recent_n = off_last3, recent_n_pct = last3_weight,
                last = off_last1, last_pct = last1_weight
            )
            team_dict["off_adj"] = off_adj

            team_def_row = def_soup.find("a", href=team_link).parent.parent

            team_def_cells = team_def_row.find_all("td")

            def_avg = float(team_def_cells[2]["data-sort"])
            team_dict["def_avg"] = def_avg

            def_last3 = float(team_def_cells[3]["data-sort"])
            team_dict["def_last3"] = def_last3

            def_last1 = float(team_def_cells[4]["data-sort"])
            team_dict["def_last1"] = def_last1

            def_adj = adjust_stat(
                avg = def_avg, avg_pct = avg_weight,
                recent_n = def_last3, recent_n_pct = last3_weight,
                last = def_last1, last_pct = last1_weight
            )
            if "NCAAB" == target_sport and def_adj >= 1.10:
                def_adj = 1.10
            team_dict["def_adj"] = def_adj

            team_tem_row = tem_soup.find("a", href=team_link).parent.parent
            team_tem_cells = team_tem_row.find_all("td")

            tem_avg = float(team_tem_cells[2]["data-sort"])
            team_dict["tem_avg"] = tem_avg
            
            tem_last3 = float(team_tem_cells[3]["data-sort"])
            team_dict["tem_last3"] = tem_last3
            
            tem_last1 = float(team_tem_cells[4]["data-sort"])
            team_dict["tem_last1"] = tem_last1

            tem_adj = adjust_stat(
                avg = tem_avg, avg_pct = avg_weight,
                recent_n = tem_last3, recent_n_pct = last3_weight,
                last = tem_last1, last_pct = last1_weight
            )
            team_dict["tem_adj"] = tem_adj


        odds_text = match_soup.find("p", class_="h1-sub").find("strong").text
        market_spread = 0
        market_total = 0
        if " by " in odds_text:
            market_spread = odds_text.split("Odds:")[1].split(" by ")[1].split(',')[0]
            market_total = match_soup.find("p", class_="h1-sub").find("strong").text.split("Odds:")[1].split(" by ")[1].split(',')[1].split(":")[1].strip()

            market_spread = float(market_spread)
            market_spread = np.abs(market_spread)
            market_total = float(market_total)
            match_dict["total_odds"] = market_total
            match_dict["spread_odds"] = market_spread
        else:
            st.write("Couldn't find valid odds")
        match_dict["teams"] = team_list

        match_dict["neutral"] = neutral
        match_dict["projected_tem"] = (
            match_dict["teams"][0]["tem_adj"] + match_dict["teams"][1]["tem_adj"]
        ) / 2

        match_dict["teams"][0]["projection"] = j_projection(
            protag_off_eff = match_dict["teams"][0]["off_adj"],
            antag_def_eff = match_dict["teams"][1]["def_adj"],
            lae = lao,
            projected_tem = match_dict["projected_tem"]
        )

        match_dict["teams"][1]["projection"] = j_projection(
            protag_off_eff = match_dict["teams"][1]["off_adj"],
            antag_def_eff = match_dict["teams"][0]["def_adj"],
            lae = lao,
            projected_tem = match_dict["projected_tem"]
        )

        match_teams_df = pd.DataFrame(
            match_dict["teams"]
        )

        projected_tem = np.mean([
            match_dict["teams"][0]["tem_adj"],
            match_dict["teams"][1]["tem_adj"]
        ])

        teams_df = pd.DataFrame(
            match_dict["teams"]
        )

        tr_fav_name = match_soup.select(".matchup-table > tbody > tr > td")[0].text.strip()
        tr_fav_idx = teams_df[teams_df["name"] == tr_fav_name].index

        sd_total = sport_details[target_sport]["std_dev"]["total"]

        sd_spread = sport_details[target_sport]["std_dev"]["spread"]

        teams_df["home"] = np.where(teams_df["home"] == True, "home", "away")

        teams_df = teams_df[["name", "home", "off_adj", "def_adj", "tem_adj", "projection"]]

        teams_df.rename(columns={
            "home": "place",
            "off_adj": "off",
            "def_adj": "def",
            "tem_adj": "tem",
            "projection": "j_proj"
        }, inplace=True)

        teams_df.columns = [col.upper() for col in teams_df.columns]

        teams_df.loc[0, "M_PROJ"] = (
            (
                teams_df.loc[0, "OFF"]
                +
                teams_df.loc[1, "DEF"]
            ) / 2 
            * teams_df.loc[0, "TEM"]
        )
        
        teams_df.loc[1, "M_PROJ"] = (
            (
                teams_df.loc[1, "OFF"]
                +
                teams_df.loc[0, "DEF"]
            ) / 2 
            * teams_df.loc[1, "TEM"]
        )

        teams_df.loc[0, "R_PROJ"] = r_projection(
            protag_off_eff = teams_df.loc[0, "OFF"],
            antag_def_eff = teams_df.loc[1, "DEF"],
            lae = lao,
            proj_tem = projected_tem
        )

        teams_df.loc[1, "R_PROJ"] = r_projection(
            protag_off_eff = teams_df.loc[1, "OFF"],
            antag_def_eff = teams_df.loc[0, "DEF"],
            lae = lao,
            proj_tem = projected_tem
        )
        

        injury_link = f"{match_link}/injuries"
        injury_response = requests.get(injury_link)
        injury_soup = BeautifulSoup(injury_response.text, "html.parser")
        injury_tables = injury_soup.find_all("table")
        injured_players = {}
        has_injured_players = False

        for i, table in enumerate(injury_tables):
            injury_rows = table.find_all("tr")
            injury_count = 0
            team_name = teams_df.loc[i, "NAME"]
            
            injured_players[team_name] = []

            for row in injury_rows:
                if len(row.select("td[class=nowrap]")) > 0:                
                    injury_count = len(injury_rows) - 1
                    has_injured_players = True
                    all_tds = row.find_all("td")
                    player_name = all_tds[0].text
                    injury_time = all_tds[2].text
                    
                    injured_players[team_name].append(f"{player_name} ({injury_time})")
                else:
                    injury_count = 0 

        if not neutral:
            teams_df.loc["home" == teams_df["PLACE"], ["J_PROJ", "M_PROJ"]] += hca
        
        j_proj_total = teams_df["J_PROJ"].sum()
        m_proj_total = teams_df["M_PROJ"].sum()
        r_proj_total = teams_df["R_PROJ"].sum()

        z_total = (j_proj_total - market_total) / sd_total
        table_total = make_table_score(z_total)
        wager_total = "over"
        if z_total < 0:
            table_total = 100 - table_total
            wager_total = "under"

        market_fav_idx = teams_df.loc[(tr_fav_name == teams_df["NAME"]), :].index
        underdog_idx = teams_df.loc[(tr_fav_name != teams_df["NAME"]), :].index

        j_margin = (
            teams_df.loc[market_fav_idx, "J_PROJ"].item()
            -
            teams_df.loc[underdog_idx, "J_PROJ"].item()
        )

        m_margin = (
            teams_df.loc[market_fav_idx, "M_PROJ"].item()
            -
            teams_df.loc[underdog_idx, "M_PROJ"].item()
        )

        r_margin = (
            teams_df.loc[market_fav_idx, "R_PROJ"].item()
            -
            teams_df.loc[underdog_idx, "R_PROJ"].item()
        )

        z_spread = (j_margin - market_spread) / sd_spread
        table_spread = make_table_score(z_spread)
        wager_spread = "favorite"
        if z_spread < 0:
            table_spread = 100 - table_spread
            wager_spread = "underdog"

        m_proj_total = teams_df["M_PROJ"].sum(axis=0)

        odds_df = pd.DataFrame()

        if market_total:
            odds_df.loc["total", "MARKET"] = market_total
            odds_df.loc["total", "J_PROJ"] = j_proj_total
            odds_df.loc["total", "M_PROJ"] = m_proj_total
            odds_df.loc["total", "R_PROJ"] = r_proj_total
            odds_df.loc["total", "J_GAP"] = j_proj_total - market_total        
            odds_df.loc["total", "M_GAP"] = m_proj_total - market_total
            odds_df.loc["total", "R_GAP"] = r_proj_total - market_total

        if market_spread:
            odds_df.loc["spread", "MARKET"] = market_spread
            odds_df.loc["spread", "J_PROJ"] = j_margin
            odds_df.loc["spread", "M_PROJ"] = m_margin
            odds_df.loc["spread", "R_PROJ"] = r_margin
            odds_df.loc["spread", "J_GAP"] = j_margin - market_spread
            odds_df.loc["spread", "M_GAP"] = m_margin - market_spread
            odds_df.loc["spread", "R_GAP"] = r_margin - market_spread

        if market_total or market_spread:
            odds_df["J_GAP"] = odds_df["J_GAP"].map(
                lambda x: f"+{np.round(x, 2)}" if x > 0 else np.round(x, 2)
            )
            odds_df["M_GAP"] = odds_df["M_GAP"].map(
                lambda x: f"+{np.round(x, 2)}" if x > 0 else np.round(x, 2)
            )        
            odds_df["R_GAP"] = odds_df["R_GAP"].map(
                lambda x: f"+{np.round(x, 2)}" if x > 0 else np.round(x, 2)
            )
                

        wager_df = pd.DataFrame({
            "z_value": [z_total, z_spread],
            "table": [table_total, table_spread],
            "wager": [wager_total, wager_spread]
        }, index = ["total", "spread"])
        
        st.write(f"FAVORITE: {teams_df.loc[market_fav_idx, "NAME"].item()}")
        st.write(f"UNDERDOG: {teams_df.loc[underdog_idx, "NAME"].item()}")
        st.dataframe(teams_df.round(2), hide_index = True)
            
        st.write(f"PROJ PACE: {projected_tem.round(2)}")

        if market_total or market_spread:
            st.write("Odds:\n")
            st.write(odds_df.round(2))
        if not market_total:
            st.write("True total:")
            st.write(np.round(j_proj_total, 2))
        if not market_spread:
            st.write("True spread:")
            st.write(np.round(j_margin, 2))
            
        if market_spread and market_total:
            st.write("Z-Scores:")
            st.write(wager_df)

        st.divider()



load_btn = st.button(
    label = "Load Results",
    on_click = handle_load_btn
)

