from read_map import MapParser, ParseError
def main() -> None:
    map = MapParser("01_linear_path.txt")
    try:
        map.check_map()
    except ParseError as e:
        print(e)
    
if __name__=="__main__":
    main()