module M = {
  var x : int  :: private;
  var y : int  :: public;
  var z : int  :: public;

  proc f() : unit = {
    if (y < z) {
      while (y < z) {
        x <- x + y;
        y <- y + 1;
      }
    }
    elif (y = z) { }
    else {
      while (z < y) {
        x <- x + y;
        y <- y - 1;
      }
    }
  }
}
