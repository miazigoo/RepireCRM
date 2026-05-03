import { routes } from './app.routes';

describe('app routes', () => {
  function childPath(path: string) {
    return routes
      .find((route) => route.path === '')
      ?.children?.find((route) => route.path === path);
  }

  it('registers sidebar sections as routable pages', () => {
    expect(childPath('dashboard')).toBeTruthy();
    expect(childPath('orders')).toBeTruthy();
    expect(childPath('customers')).toBeTruthy();
    expect(childPath('inventory')).toBeTruthy();
    expect(childPath('reports')).toBeTruthy();
    expect(childPath('admin')).toBeTruthy();
  });
});
