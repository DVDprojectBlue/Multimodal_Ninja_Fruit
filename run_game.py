from src.game import NinjaFruitGame

def main():
    # Tu będzie można przekazywać argumenty z konsoli
    params = {
        "title": "Ninja Fruit: In progress...",
    }
    
    game = NinjaFruitGame(**params)
    game.run()

if __name__ == "__main__":
    main()