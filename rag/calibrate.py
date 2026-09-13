"""Calibration utility for retrieval similarity thresholds."""
from rag.retrieve import search, settings

IN_DOMAIN = [
    "Which category has the highest return rate?",
    "What are the major patterns in customer ratings?",
    "Which regions or categories are performing strongly?",
    "What customer segments should the business target?",
    # paraphrases / harder, single-section targets
    "What is the total revenue and average order value?",
    "How does delivery delay affect customer ratings?",
    "Which marketing channel gives the best return on acquisition cost?",
    "Which shipping method is the slowest?",
    "How much revenue comes from November and December?",
    "Why is Electronics revenue high but its margin low?",
    "Is the return rate going up or down over the years?",
    "Do coupons increase the average order value?",
    "Which region has the highest profit margin?",
    "How many customers are in the RFM 'At Risk' segment?",
]

OFF_TOPIC = [
    "What is the capital of France?",
    "Write me a poem about the sea.",
    "How do I install Python on Windows?",
    "Who won the football world cup in 2022?",
    "What is the boiling point of water at sea level?",
    "Explain how a transformer neural network works.",
    "What's a good recipe for banana bread?",
    "How many moons does Jupiter have?",
    "Translate 'good morning' into Spanish.",
    "What are the symptoms of the flu?",
]

NEAR_TOPIC = [
    "What was revenue in 2019?",
    "What is Amazon's return rate?",
    "How do I reset my password on the website?",
    "Which warehouse is in Texas?",
    "What is the customer churn rate?",
]


def best_similarity(question: str) -> tuple[float, str]:
    hits = search(question, top_k=1)
    if not hits:
        return 0.0, "(no rows)"
    return hits[0].similarity, f"{hits[0].source_file} > {hits[0].section_title}"


def report(title: str, questions: list[str]) -> list[float]:
    print(f"\n{title}")
    scores = []
    for question in questions:
        score, where = best_similarity(question)
        scores.append(score)
        print(f"  {score:.3f}  {question:<62} -> {where}")
    return scores


def main() -> None:
    in_domain = report("IN-DOMAIN (should all pass the guard)", IN_DOMAIN)
    off_topic = report("OFF-TOPIC (should all be caught by the guard)", OFF_TOPIC)
    near_topic = report("NEAR-TOPIC (expected to pass - the prompt must refuse these)", NEAR_TOPIC)

    weakest_in, strongest_off = min(in_domain), max(off_topic)
    midpoint = round((weakest_in + strongest_off) / 2, 2)
    print(f"\nweakest in-domain hit : {weakest_in:.3f}")
    print(f"strongest off-topic   : {strongest_off:.3f}")
    print(f"gap                   : {weakest_in - strongest_off:.3f}")
    print(f"midpoint (recommended): {midpoint:.2f}")
    print(f"configured threshold  : {settings.rag_similarity_threshold:.2f}")
    near_pass = sum(s >= settings.rag_similarity_threshold for s in near_topic)
    print(f"near-topic passing the configured guard: {near_pass}/{len(near_topic)} (expected - prompt's job)")


if __name__ == "__main__":
    main()
