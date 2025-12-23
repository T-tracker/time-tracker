from app import create_app

app = create_app()

# Отладка маршрутов
@app.route('/debug/routes')
def debug_routes():
    import json
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
    return json.dumps(routes, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    app.run(debug=True)
