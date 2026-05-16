import { INVENTORY_ROUTES } from './inventory.routes';

describe('inventory routes', () => {
  it('registers dashboard and creation pages', () => {
    expect(INVENTORY_ROUTES.map(route => route.path)).toEqual([
      '',
      'items/new',
      'purchase-requests',
      'purchase-requests/new',
      'purchase-orders/new'
    ]);
  });
});
