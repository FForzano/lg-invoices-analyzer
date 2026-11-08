import { describe, expect, it } from 'vitest';
import { eur, num, pctSigned } from './format';

describe('formati italiani', () => {
  it('euro con virgola e spazio per le migliaia', () => {
    expect(eur(1234.5)).toBe('1 234,50 €');
    expect(eur(-12.48)).toBe('-12,48 €');
    expect(eur(null)).toBe('–');
  });
  it('numeri con decimali scelti', () => {
    expect(num(3388, 0)).toBe('3 388');
    expect(num(0.1234, 3)).toBe('0,123');
  });
  it('variazioni percentuali col segno', () => {
    expect(pctSigned(5.04)).toBe('+5,0%');
    expect(pctSigned(-2)).toBe('-2,0%');
    expect(pctSigned(null)).toBeNull();
  });
});
