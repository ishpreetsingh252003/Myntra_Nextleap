"""Theme clustering — groups evidence packets into thematic clusters.

Uses TF-IDF embeddings from Phase 4 (or generates new ones) + scikit-learn
clustering (KMeans / Agglomerative). Each cluster gets a keyword-based label.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score


def cluster_packets(packets: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    """Cluster evidence packets by their text. Returns cluster assignments + labels."""
    clustering_cfg = cfg.get("clustering", {})
    method = clustering_cfg.get("method", "kmeans")
    n_clusters = int(clustering_cfg.get("n_clusters", 5))

    texts = [f"{p.get('quote', '')} {' '.join(p.get('behaviours', []))} {' '.join(p.get('barriers', []))}" for p in packets]
    if len(texts) < 2:
        return {"labels": [0] * len(texts), "n_clusters": 1, "cluster_labels": {}, "silhouette": 0.0}

    vectorizer = TfidfVectorizer(max_features=300, stop_words="english", ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts).toarray()

    # auto-determine n_clusters if too large
    if n_clusters >= len(texts):
        n_clusters = max(2, len(texts) // 3)

    if method == "kmeans":
        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = model.fit_predict(X)
    else:
        model = AgglomerativeClustering(n_clusters=n_clusters)
        labels = model.fit_predict(X)

    # generate cluster labels from top TF-IDF terms
    feature_names = vectorizer.get_feature_names_out()
    cluster_labels: dict[int, str] = {}
    for cluster_id in range(n_clusters):
        mask = labels == cluster_id
        if mask.sum() == 0:
            cluster_labels[cluster_id] = f"cluster_{cluster_id}"
            continue
        centroid = X[mask].mean(axis=0)
        top_indices = centroid.argsort()[-3:][::-1]
        top_terms = [feature_names[i] for i in top_indices]
        cluster_labels[cluster_id] = " / ".join(top_terms)

    sil = float(silhouette_score(X, labels)) if len(set(labels)) > 1 else 0.0
    return {
        "labels": labels.tolist(),
        "n_clusters": n_clusters,
        "cluster_labels": cluster_labels,
        "silhouette": round(sil, 3),
    }
