# 接口文档 — `/news/locations/articles/with-location`

## 概述

获取指定类别和时间段内的新闻文章（带地理位置信息）的列表。

---

## 请求

| 方法 | 路径                                       | 描述                     |
| ---- | ------------------------------------------ | ------------------------ |
| GET  | `/news/locations/articles/with-location` | 按类别和时间查询新闻文章 |

---

## 请求参数

### 查询参数 (Query)

| 参数名     | 类型   | 必填 | 说明                            | 示例                    |
| ---------- | ------ | ---- | ------------------------------- | ----------------------- |
| category   | string | 是   | 新闻类别                        | `business`            |
| start_time | string | 是   | 起始时间，ISO 8601 日期时间格式 | `2025-05-01T00:00:00` |
| end_time   | string | 是   | 结束时间，ISO 8601 日期时间格式 | `2025-07-04T00:00:00` |

---

## 请求示例

```
GET /news/locations/articles/with-location?category=business&start_time=2025-05-01T00:00:00&end_time=2025-07-04T00:00:00
```

---

## 响应示例

```json
{
  "totalResults": 143,
  "articles": [
    {
      "source": {
        "id": "the-wall-street-journal",
        "name": "The Wall Street Journal"
      },
      "author": "WSJ",
      "title": "Stock Market Today: Dow Futures Fall; OECD Cuts U.S. Growth Outlook – Live Updates - WSJ",
      "description": null,
      "url": "https://www.wsj.com/livecoverage/stock-market-today-trump-tariffs-trade-war-06-03-2025",
      "urlToImage": null,
      "publishedAt": "2025-06-03T08:00:00Z",
      "content": "……"
    }
  ]
}
```

---

## 响应字段说明

| 字段             | 类型            | 说明                       |
| ---------------- | --------------- | -------------------------- |
| totalResults     | integer         | 本次查询符合条件的新闻总数 |
| articles         | array           | 新闻文章列表               |
| ├─ source      | object          | 新闻来源信息               |
| │  ├─ id      | string          | 新闻源唯一标识             |
| │  └─ name    | string          | 新闻源名称                 |
| ├─ author      | string          | 文章作者                   |
| ├─ title       | string          | 文章标题                   |
| ├─ description | string/nullable | 文章摘要或描述             |
| ├─ url         | string          | 文章链接                   |
| ├─ urlToImage  | string/nullable | 文章配图链接               |
| ├─ publishedAt | string          | 发布时间，ISO 8601 格式    |
| └─ content     | string          | 文章内容简要或全文         |

---

## 注意事项

* 时间格式要求严格遵守 ISO 8601 标准（示例：2025-05-01T00:00:00）。(待)
* `category` 参数需要准确填写支持的类别名称。
* 返回结果中某些字段（如 `description`, `urlToImage`）可能为null。
* 下一步拟将地名识别和位置编码放到数据更新时，待待。
