// ─── Mock Data for all services ───
// Matches the provided UI screenshots exactly

export const mockUsers = {
  admin: { username: 'admin', password: 'admin123', role: 'Admin', access_token: 'mock-token-admin' },
  curator: { username: 'curator', password: 'curator123', role: 'Curator', access_token: 'mock-token-curator' },
  analyst: { username: 'analyst', password: 'analyst123', role: 'Analyst', access_token: 'mock-token-analyst' },
  user: { username: 'user', password: 'user123', role: 'User', access_token: 'mock-token-user' },
}

export const mockAuditLog = [
  {
    id: 1,
    ts: '2026-03-11T10:45:12Z',
    actor: 'jan.novak',
    role: 'Admin',
    event_type: 'THRESHOLD CHANGE',
    event_category: 'threshold',
    detail: 'změna z 75% → 80%',
    operation_id: 'op-a1b2c3d4',
    request_id: 'req-001',
  },
  {
    id: 2,
    ts: '2026-03-11T10:45:12Z',
    actor: 'eva.curator',
    role: 'Analyst',
    event_type: 'TEST RUN',
    event_category: 'test',
    detail: 'Spuštěn test ob-8f92',
    operation_id: 'op-e5f6g7h8',
    request_id: 'req-002',
  },
  {
    id: 3,
    ts: '2026-03-11T10:45:12Z',
    actor: 'petr.curator',
    role: 'User',
    event_type: 'LOGIN',
    event_category: 'login',
    detail: 'Login in...',
    operation_id: 'op-i9j0k1l2',
    request_id: 'req-003',
  },
  {
    id: 4,
    ts: '2026-03-11T10:45:12Z',
    actor: 'petr.curator',
    role: 'System',
    event_type: 'CAPTCHA ERROR',
    event_category: 'error',
    detail: 'URL blocked',
    operation_id: 'op-m3n4o5p6',
    request_id: 'req-004',
  },
  {
    id: 5,
    ts: '2026-03-11T09:30:00Z',
    actor: 'admin',
    role: 'Admin',
    event_type: 'COMPLIANCE CONFIRM',
    event_category: 'compliance',
    detail: 'Ingest potvrzení – source:12',
    operation_id: 'op-q7r8s9t0',
    request_id: 'req-005',
    compliance_bypassed: false,
  },
  {
    id: 6,
    ts: '2026-03-10T14:20:00Z',
    actor: 'curator',
    role: 'Curator',
    event_type: 'INGEST',
    event_category: 'ingest',
    detail: 'Ingest google.com – 15 chunks',
    operation_id: 'op-u1v2w3x4',
    request_id: 'req-006',
  },
  {
    id: 7,
    ts: '2026-03-10T13:00:00Z',
    actor: 'user',
    role: 'User',
    event_type: 'QUERY',
    event_category: 'query',
    detail: 'RAG dotaz: "Jak funguje systém?"',
    operation_id: 'op-y5z6a7b8',
    request_id: 'req-007',
  },
  {
    id: 8,
    ts: '2026-03-10T11:00:00Z',
    actor: 'analyst',
    role: 'Analyst',
    event_type: 'QUERY',
    event_category: 'query',
    detail: 'No-RAG dotaz: benchmark test',
    operation_id: 'op-c9d0e1f2',
    request_id: 'req-008',
  },
]

export const mockSources = [
  {
    id: 1,
    name: 'Google',
    url: 'google.com',
    base_url: 'https://google.com',
    strategy: 'HTTP',
    status: 'CAPTCHA',
    frequency: 'Denně',
    last_crawl: '2026-03-08',
    permission_type: 'public',
  },
  {
    id: 2,
    name: 'UIS Mandelu',
    url: 'uis.mandelu.cz',
    base_url: 'https://uis.mandelu.cz',
    strategy: 'SCREENSHOT',
    status: 'OK',
    frequency: 'Týdně',
    last_crawl: '2026-03-08',
    permission_type: 'public',
  },
  {
    id: 3,
    name: 'EUR-Lex',
    url: 'eur-lex.europa.eu',
    base_url: 'https://eur-lex.europa.eu',
    strategy: 'HTTP',
    status: 'OK',
    frequency: 'Měsíčně',
    last_crawl: '2026-03-01',
    permission_type: 'public',
  },
]

export const mockIncidents = [
  {
    id: 1,
    type: 'CAPTCHA',
    url: 'protected-site.com/page-42',
    source_id: 1,
    status: 'open',
    created_ts: '2026-03-08T09:30:00Z',
  },
  {
    id: 2,
    type: 'CAPTCHA',
    url: 'protected-site.com/page-55',
    source_id: 1,
    status: 'open',
    created_ts: '2026-03-08T10:15:00Z',
  },
]

export const mockSettings = {
  retention: {
    raw_evidence: '60 dní',
    audit_logs: '60 dní',
    vector_snapshot: '60 dní',
  },
  compliance_enforcement: false,
}

export const mockComplianceHistory = [
  {
    id: 1,
    user: 'admin',
    action: 'ingest.run',
    timestamp: '2026-03-11T10:40:00Z',
    operation_id: 'op-q7r8s9t0',
    reason: 'Pravidelný sběr dat',
    confirmed: true,
  },
  {
    id: 2,
    user: 'curator',
    action: 'ingest.run',
    timestamp: '2026-03-10T14:15:00Z',
    operation_id: 'op-u1v2w3x4',
    reason: 'Nový zdroj – první ingest',
    confirmed: true,
  },
  {
    id: 3,
    user: 'curator',
    action: 'query.execute',
    timestamp: '2026-03-10T12:00:00Z',
    operation_id: 'op-bypass-01',
    reason: '',
    confirmed: false,
    compliance_bypassed: true,
  },
]

export const mockQueryResponse = {
  rag: {
    mode: 'rag',
    answer: 'Na základě dostupných dokumentů je systém navržen tak, aby umožňoval multimodální vyhledávání a odpovídání na dotazy pomocí RAG (Retrieval Augmented Generation). Systém kombinuje textové chunky s vizuálními artefakty pro komplexní odpovědi.\n\nKlíčové komponenty:\n1. **Embedding pipeline** – převod textu na vektorové reprezentace\n2. **Retrieval engine** – vyhledávání relevantních dokumentů\n3. **Ollama answering** – generování odpovědí s citacemi',
    citations: [
      {
        index: 1,
        url: 'https://example.com/docs/architecture',
        score: 0.892,
        source_id: 1,
        doc_id: 1,
        chunk_id: 1,
        chunk_type: 'text',
        evidence: { evidence_ids: [101, 102] },
      },
      {
        index: 2,
        url: 'https://example.com/docs/rag-pipeline',
        score: 0.847,
        source_id: 1,
        doc_id: 2,
        chunk_id: 3,
        chunk_type: 'text',
        evidence: { evidence_ids: [103] },
      },
      {
        index: 3,
        url: 'https://example.com/docs/embedding',
        score: 0.781,
        source_id: 2,
        doc_id: 5,
        chunk_id: 8,
        chunk_type: 'text',
        evidence: { evidence_ids: [108] },
      },
    ],
  },
  noRag: {
    mode: 'no-rag',
    answer: 'Jako jazykový model mohu poskytnout obecné informace o RAG systémech. RAG (Retrieval Augmented Generation) je architektonický vzor, který kombinuje vyhledávání v databázi dokumentů s generativním jazykovým modelem pro přesnější a faktuálně podložené odpovědi.',
    citations: [],
  },
}

export const mockDashboardStats = {
  totalSources: 23,
  openIncidents: 3,
  lastCrawl: '2026-03-08',
  nextCrawl: '2026-03-15',
  totalDocuments: 1247,
  totalChunks: 8934,
  queriesLast24h: 42,
}

export const mockChatSessions = [
  {
    id: 'session-1234',
    title: 'Analýza dokumentace k systému',
    updated_at: '2026-04-08T10:30:00Z',
    messages: [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Jak funguje RAG?',
        timestamp: '2026-04-08T10:25:00Z'
      },
      {
        id: 'msg-2',
        role: 'ai',
        content: 'RAG (Retrieval Augmented Generation) funguje připojením vyhledávací vrstvy před generativní model v Ollamě. Systém nejprve najde relevantní dokumenty a ty předloží modelu jako kontext.',
        timestamp: '2026-04-08T10:25:05Z',
        citations: []
      },
      {
        id: 'msg-3',
        role: 'user',
        content: 'Jaké databáze používá náš systém?',
        timestamp: '2026-04-08T10:29:00Z'
      },
      {
        id: 'msg-4',
        role: 'ai',
        content: 'Náš systém používá vektorovou databázi pro ukádání embeddingů a relační databázi pro aplikační data.',
        timestamp: '2026-04-08T10:29:07Z',
        citations: [
          { index: 1, url: 'https://example.com/docs/architecture', score: 0.95 }
        ]
      }
    ]
  },
  {
    id: 'session-5678',
    title: 'Testování rychlosti',
    updated_at: '2026-04-07T14:15:00Z',
    messages: [
      {
        id: 'msg-5',
        role: 'user',
        content: 'Ahoj, jak jsi rychlý?',
        timestamp: '2026-04-07T14:15:00Z'
      },
      {
        id: 'msg-6',
        role: 'ai',
        content: 'Při běžném vytížení odpovídám obvykle do 2 sekund.',
        timestamp: '2026-04-07T14:15:02Z',
        citations: []
      }
    ]
  }
]

export const mockIngestResult = {
  status: 'completed',
  source_id: 1,
  url: 'https://google.com/about',
  strategy: 'html',
  documents_created: 1,
  chunks_created: 15,
  quality_score: 0.82,
  operation_id: null, // Will be set dynamically
  batch_id: null,
}
