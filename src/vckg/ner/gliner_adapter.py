"""GLiNER2.5 adapter (real model only; no mock here). Import of torch/gliner2 is lazy so that
enter-project.ps1 environment variables are always applied first."""
from __future__ import annotations

from vckg.models import EntityType, Mention

LABELS = {
    "person": "Names of people, e.g. business leaders, executives, shareholders",
    "company": "Companies, corporations, groups, joint-stock or limited companies",
    "bank": "Commercial banks and financial institutions",
    "regulator": "Financial regulators such as the State Securities Commission or the State Bank",
    "government agency": "Ministries, government bodies, inspectorates, police and courts",
}
LABEL_TO_TYPE = {
    "person": EntityType.PERSON,
    "company": EntityType.ORGANIZATION,
    "bank": EntityType.BANK,
    "regulator": EntityType.REGULATOR,
    "government agency": EntityType.GOVERNMENT_AGENCY,
}


class GlinerNER:
    def __init__(self, model_id: str = "fastino/gliner2.5-multi-v1", device: str = "cuda",
                 threshold: float = 0.5, quantize: bool = True):
        from gliner2 import AutoExtractor  # lazy

        self.model_id, self.threshold = model_id, threshold
        self.model = AutoExtractor.from_pretrained(model_id, map_location=device, quantize=quantize and device == "cuda")

    def extract(self, text: str) -> list[Mention]:
        res = self.model.extract_entities(
            text, LABELS, include_confidence=True, include_spans=True, threshold=self.threshold
        )
        return self.parse(res, text)

    def extract_long(self, text: str, chunk_size: int = 384, overlap: int = 64) -> list[Mention]:
        res = self.model.extract_entities_long(
            text, LABELS, chunk_size=chunk_size, chunk_overlap=overlap,
            include_confidence=True, include_spans=True, threshold=self.threshold,
        )
        return self.parse(res, text)

    def extract_sentences(self, text: str, sentences, batch_size: int = 16) -> list[Mention]:
        """Sentence-level batch inference (Phase 4): offsets are shifted back to article coordinates. Sentence-level
        input avoided whole-article misses seen on real text (e.g. a company name found only per sentence)."""
        if not sentences:
            return []
        results = self.model.batch_extract_entities(
            [s.text for s in sentences], LABELS, batch_size=batch_size, include_confidence=True,
            include_spans=True, threshold=self.threshold)
        out: list[Mention] = []
        for s, res in zip(sentences, results, strict=True):
            for m in self.parse(res, s.text):
                a, b = m.start + s.start, m.end + s.start
                if text[a:b] == m.text:
                    out.append(m.model_copy(update={"start": a, "end": b}))
        return sorted(out, key=lambda m: (m.start, -m.end))

    @staticmethod
    def parse(res: dict, text: str) -> list[Mention]:
        out: list[Mention] = []
        for label, items in res.get("entities", {}).items():
            etype = LABEL_TO_TYPE.get(label)
            if etype is None:
                continue
            for it in items:
                s, e = it["start"], it["end"]
                if text[s:e] != it["text"]:  # offset sanity: drop rather than guess
                    continue
                out.append(Mention(text=it["text"], start=s, end=e, label=etype,
                                   confidence=float(it.get("confidence", 0.0)), method="gliner2.5"))
        return sorted(out, key=lambda m: (m.start, -m.end))

