// Forme delle risposte di /api (vedi app/api/*). Le dataclass del backend sono serializzate così come sono.
export type Commodity = 'power' | 'gas';
export type MessageLevel = 'info' | 'warn';
export interface Message { level: MessageLevel; text: string }

export interface User { id: number; email: string; name: string; is_admin: boolean; must_change_password: boolean; created_at: string; profiles?: number }

/** Risposta di POST /simulate: la simulazione pubblica da una sola bolletta (nulla viene salvato). */
export interface Simulation {
  commodity: Commodity; method: string; catalog_size: number;
  bill: { supplier: string | null; period_start: string; period_end: string; consumption: number | null; total_eur: number | null; reading_type: string | null };
  analysis: Omit<Analysis, 'settings'>;
  current_offer: { name: string; supplier: string } | null;
  alternatives: Ranked[];
}

export interface Profile { id: number; name: string; region: string; province: string; comune: string; default_power_kw: number; bills?: number }

export interface Bill {
  id: number; commodity: Commodity; period_start: string; period_end: string; supplier: string | null;
  consumption: number | null; reading_type: string | null; total_eur: number | null; pdf_path: string | null;
}
export interface Offer {
  id: number | null; commodity: Commodity; supplier: string; name: string; price_type: 'fixed' | 'indexed';
  expires_on: string | null; is_current: boolean; dual_with: string | null; source: string | null;
  duration_months: number | null; conditions: string | null; after_term: string | null; exit_terms: string | null; bonus_terms: string | null; residency: 'resident' | 'non_resident' | null; power_min: number | null; power_max: number | null; consumption_min: number | null; consumption_max: number | null; valid_for: string | null; activation_channels: string | null; index_name: string | null; payment_methods: string | null; activation_terms: string | null; phone: string | null; offer_url: string | null;
  [key: string]: unknown;
}
export interface Estimate { energy: number; fixed_fee: number; power_fee: number; discount: number; total: number }
export interface Ranked { offer: Offer; estimate: Estimate; saving: number | null }
export interface Bundle { power: Ranked; gas: Ranked; total: number; saving: number | null }
export interface Consumption { total: number; bands: [number, number, number] | null; power_kw: number | null; source: string; days_covered: number; partial: boolean }
export interface Assumptions { pun: number; psv: number; default_power_kw: number; loss_pct: number; dispatching_extra: number }
export interface Verdict {
  current: Ranked; best: Ranked; saving: number; saving_pct: number; saving_range: [number, number]; worthwhile: boolean; robust: boolean;
}
export interface DualVerdict { best: Bundle; saving: number; saving_pct: number; separate_saving: number; worthwhile: boolean; beats_separate: boolean }
export interface ProposalVerdict {
  proposal: Estimate; current: Estimate; saving: number; saving_pct: number; saving_steady: number; saving_range: [number, number]; worthwhile: boolean; robust: boolean;
}
export interface PowerAdvice { contracted: number; peak: number; months: number; suggested: number | null; saving_year: number | null; partial: boolean; tight: boolean }
export interface Analysis {
  commodity: Commodity; settings: Settings; consumption: Consumption | null; assumptions: Assumptions | null; skipped: string[];
  verdict: Verdict | null; has_current: boolean; power_advice: PowerAdvice | null; season_multiplier: number;
}
export type Settings = Record<string, number | string>;
export interface PageInfo { number: number; pages: number; total: number }
export interface HistoryRow { bill: Bill; unit_cost: number | null; consumption_yoy: number | null; unit_cost_yoy: number | null }
export interface ChartData { labels: string[]; consumption: (number | null)[]; total: (number | null)[]; unit_cost: (number | null)[]; estimated: boolean[] }
export interface Rule { field: string; kind: string; anchor: string; side: string; index: number; value: string | null }
export interface Layout { id: number | null; name: string; signature: string; rules: Rule[]; builtin: boolean }
export interface TeachInfo {
  pdf: string; text: string; kinds: Record<string, string>; found: Record<string, string>; samples: Record<string, string>;
  errors: Record<string, string>; help: Record<string, string>; required: string[]; choices: Record<string, string[]>;
  labels: Record<string, string>; supplier: string;
}
export interface Prefill { values: Record<string, unknown>; teach_pdf: string | null; messages: Message[] }
export interface ProposalValues { id: number | null; contact: string | null; received_on: string | null; notes: string | null; created_at?: string; [key: string]: unknown }

/** Chi gestisce l'installazione e quali funzioni opzionali sono attive (GET /api/site, pubblico): piè di pagina, termini e privacy. */
export interface Site {
  operator: { name: string; email: string; address: string; vat: string; registry: string };
  auth_enabled: boolean; registration_open: boolean; mail_enabled: boolean; llm_enabled: boolean; ads_enabled: boolean;
  storage: string; database: string;
}
export const NO_SITE: Site = { operator: { name: '', email: '', address: '', vat: '', registry: '' }, auth_enabled: false, registration_open: false, mail_enabled: false, llm_enabled: false, ads_enabled: false, storage: 'local', database: 'sqlite' };
/** Un contenuto sponsorizzato (GET /api/ads?slot=…). */
export interface Ad { sponsor: string; title: string; text: string; cta: string; url: string; image: string | null; video: string | null; alt: string }

/** Un insieme di filtri salvato per il profilo (query = ?type=fixed&no_exit=1…). */
export interface FilterPreset { id: number; name: string; query: string; is_default: boolean }
