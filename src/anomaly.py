
from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
import numpy as np

from .parser import Block
from .signature import ParsedCell, formula_to_signature


@dataclass
class Anomaly:
    sheet: str
    address: str
    formula: str
    signature: str
    orientation: str
    block_key: int
    block_size: int
    majority_signature: str
    majority_share: float 
    confidence: float 
    example_conforming_cell: Optional[ParsedCell] 


def _confidence(majority_share: float, block_size: int) -> float:
    size_weight = min(block_size / 10.0, 1.0) 
    return round(float(majority_share * (0.5 + 0.5 * size_weight)), 3)


def detect_anomalies(blocks: List[Block], min_majority_share: float = 0.6) -> List[Anomaly]:
    anomalies: List[Anomaly] = []

    for block in blocks:
        sigs = [formula_to_signature(c.formula, c.row, c.col) for c in block.cells]
        sig_series = pd.Series(sigs)
        counts = sig_series.value_counts()
        majority_sig = counts.index[0]
        majority_count = int(counts.iloc[0])
        majority_share = majority_count / len(block.cells)

        if majority_share < min_majority_share:
            continue 
        if majority_share == 1.0:
            continue 


        conforming_cell = next(
            (c for c, s in zip(block.cells, sigs) if s == majority_sig), None
        )

        for cell, sig in zip(block.cells, sigs):
            if sig != majority_sig:
                anomalies.append(
                    Anomaly(
                        sheet=cell.sheet,
                        address=cell.address,
                        formula=cell.formula,
                        signature=sig,
                        orientation=block.orientation,
                        block_key=block.key,
                        block_size=len(block.cells),
                        majority_signature=majority_sig,
                        majority_share=round(majority_share, 3),
                        confidence=_confidence(majority_share, len(block.cells)),
                        example_conforming_cell=conforming_cell,
                    )
                )

    return anomalies


def dedupe_keep_best(anomalies: List[Anomaly]) -> List[Anomaly]:
    best: dict = {}
    for a in anomalies:
        key = (a.sheet, a.address)
        if key not in best or a.confidence > best[key].confidence:
            best[key] = a
    return sorted(best.values(), key=lambda a: -a.confidence)
