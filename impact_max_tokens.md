
👉 **Ce paramètre n’est pas un simple compteur d’arrêt : il est utilisé comme un signal d’allocation mémoire côté serveur.**

---

# 1. OpenAI — Production Best Practices

[https://platform.openai.com/docs/guides/production-best-practices](https://platform.openai.com/docs/guides/production-best-practices)

**Points importants :**

* Guide officiel des bonnes pratiques de déploiement LLM.
* Passages clés :

  > "Requesting a large amount of generated tokens completions can lead to increased latencies."
  > "For requests with a similar token generation count, those that have a lower max_tokens parameter incur less latency."

👉 Un `max_tokens` trop élevé augmente mécaniquement la latence.

---

# 2. Article Arxiv — vLLM (PagedAttention)

[https://arxiv.org/pdf/2309.06180](https://arxiv.org/pdf/2309.06180)

**Passage clé :**

> "The pre-allocated chunk space for each request prevents memory sharing specific to decoding algorithms in existing memory."

👉 Le serveur réserve de la mémoire proportionnelle au max_tokens déclaré, ce qui empêche une mutualisation efficace et crée de la pression mémoire.

---

# 3. RunPod Blog — Introduction à vLLM

[https://www.runpod.io/blog/introduction-to-vllm-and-pagedattention](https://www.runpod.io/blog/introduction-to-vllm-and-pagedattention)

**Passages clés :**

> "Existing systems store KV cache pairs in continuous memory spaces."
> "They allocate a fixed, unbroken block of space for every request."
> "Requests to an LLM can vary in size widely, which leads to a significant waste of memory blocks."

👉 Le modèle d’allocation classique impose un bloc continu de mémoire dépendant du max_tokens, causant un gaspillage massif.

---

# 4. Anyscale — “Numbers Every LLM Developer Should Know”

[https://www.anyscale.com/blog/num-every-llm-developer-should-know](https://www.anyscale.com/blog/num-every-llm-developer-should-know)

**Passage clé :**

> "The amount of memory you need is directly proportional to the maximum number of tokens you want to generate."

👉 Mécaniquement : plus le `max_tokens` est élevé, plus la mémoire GPU réservée l’est également.

---

# 5. Article Voice.ai — Optimisation vLLM (Continuous batching)

[https://voice.ai/hub/tts/vllm-continuous-batching/](https://voice.ai/hub/tts/vllm-continuous-batching/)

**Passages clés :**

> "vLLM uses each request's declared max_tokens to reserve KV slots unless paged attention is enabled."
> "Large reservation values pre-allocate memory and can fragment GPU memory."
> "Reduce declared max_tokens whenever possible to avoid wasted memory."
> "Lower per-request declared max_tokens to avoid over-reservation."
> "Over estimating wastes memory. Under estimating forces reallocation."

👉 Le max_tokens sert de valeur d’allocation préventive, qui augmente la fragmentation si elle est surestimée.

---

**P.S. : Les architectures PagedAttention introduites par vLLM en 2024 réduisent significativement cet overhead.**
