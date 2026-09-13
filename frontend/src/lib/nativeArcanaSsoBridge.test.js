import { describe, expect, it } from 'vitest';
import { _test } from './nativeArcanaSsoBridge';

const { loginUrlFromAppOpen } = _test;

describe('nativeArcanaSsoBridge', () => {
  it('estrae ticket da https /login', () => {
    expect(
      loginUrlFromAppOpen('https://www.kor35.it/login?arcana_ticket=abc&x=1')
    ).toBe('/login?arcana_ticket=abc&x=1');
  });

  it('estrae ticket da schema kor35://', () => {
    expect(loginUrlFromAppOpen('kor35://login?arcana_ticket=tok')).toBe(
      '/login?arcana_ticket=tok'
    );
  });

  it('ignora URL senza ticket/error', () => {
    expect(loginUrlFromAppOpen('https://www.kor35.it/app')).toBeNull();
    expect(loginUrlFromAppOpen('https://www.kor35.it/login')).toBeNull();
  });
});
