from app.movie import split_story

def test_split():
    assert len(split_story("Scene one\n\nScene two\n\nScene three", 10)) == 3
