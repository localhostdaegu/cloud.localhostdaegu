"""랜드마크 → (대표 행정동, district_code). 시연 입력이 바로 먹히는 대구 별칭 사전."""
LANDMARKS: dict[str, tuple[str, str]] = {
    "서문시장": ("대신동", "27110"), "동성로": ("성내1동", "27110"), "약령시": ("성내2동", "27110"),
    "칠성시장": ("칠성동", "27230"), "평화시장": ("신암동", "27140"), "동대구역": ("신암동", "27140"),
    "안지랑": ("대명동", "27200"), "앞산": ("대명동", "27200"),
    "들안길": ("상동", "27260"), "수성못": ("두산동", "27260"), "알파시티": ("고산동", "27260"),
    "동인동": ("동인동", "27110"), "두류": ("두류동", "27290"), "계명대": ("신당동", "27290"),
    "경북대": ("산격동", "27230"),
}
INDUSTRY_SYNONYMS: dict[str, str] = {
    "카페": "rest_cafes", "커피": "rest_cafes", "디저트": "rest_cafes",
    "음식점": "general_restaurants", "식당": "general_restaurants", "고깃집": "general_restaurants",
    "곱창": "general_restaurants", "찜갈비": "general_restaurants", "치킨": "general_restaurants",
    "미용실": "beauty_salons", "헬스장": "fitness_centers", "체육관": "fitness_centers",
    "당구장": "billiard_halls", "노래방": "karaoke_rooms", "피시방": "pc_bangs", "PC방": "pc_bangs",
}
