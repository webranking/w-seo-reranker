from typing import List

from google.cloud import discoveryengine_v1 as discoveryengine

import os
from dotenv import load_dotenv

load_dotenv()

class RankerService:
    def __init__(self):

        self.client = discoveryengine.RankServiceClient()
        self.ranking_config = self.client.ranking_config_path(
            project=os.getenv("GCP_PROJECT_ID_RANKING"),
            location="global",
            ranking_config="default_ranking_config",    # todo approfondisci
        )

    def rank(self, query: str, records: List[dict]):
        ranking_records = []
        for record in records:
            ranking_records.append(
                discoveryengine.RankingRecord(
                    id=record["id"], # todo approfondisci
                    title=record["title"],     # todo approfondisci
                    content=record["text"],
                )
            )

        request = discoveryengine.RankRequest(
            ranking_config=self.ranking_config,
            model="semantic-ranker-default@latest",
            top_n=10,
            query=query,
            records=ranking_records
        )

        response = self.client.rank(request=request)
        return list(response.records)