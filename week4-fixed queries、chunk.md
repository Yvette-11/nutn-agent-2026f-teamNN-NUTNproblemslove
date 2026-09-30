## proposal
user:



## fixed queries


### Case 1：Static Knowledge Retrieval

**Query**

```text
宿舍冷氣壞掉了，要怎麼報修？
```

### Expected Decision

```text
需要外部校園知識 evidence
```

### Expected Route

```text
static_knowledge_corpus
```

---

### Case 2：No Retrieval

**Query**

```text
請把我提供的冷氣報修公告整理得更簡短。
```

### Expected Decision

```text
使用者已提供完整內容
```

### Expected Route

```text
no_retrieval
```



---

### Case 3：Live Data Required

**Query**

```text
現在冷氣報修的承辦人員有值班嗎？
```

### Expected Decision

```text
需要即時狀態資料
```

### Expected Route

```text
live_data_source
```


### Expected Failure Code

```text
LIVE_DATA_REQUIRED
```

---

## Summary

| Case | Query 類型 | Expected Route | Retrieval |
|---|---|---|---|
| Case 1 | 校園固定知識 | `static_knowledge_corpus` | Yes |
| Case 2 | 使用者已提供內容 | `no_retrieval` | No |
| Case 3 | 即時狀態 | `live_data_source` | No static retrieval |

---



##chunk
