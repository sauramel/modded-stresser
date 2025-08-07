from config import MODE

if MODE == "controller":
    import uvicorn
    from controller import app
    uvicorn.run(app, host="0.0.0.0", port=8000)
else:
    from actor import actor_loop
    actor_loop()
