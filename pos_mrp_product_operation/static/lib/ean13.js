(function(){
    function create_ean13(code) {
      var sum=0;
      var digit, ean_code;
      
      // left pading
      var pad = "000000000000"
      var ean_code = code.replace(/\D/g,'');
      ean_code = pad.substring(0, pad.length - ean_code.length) + ean_code
      
      for(var i=0; i<12; i++) {
        digit = parseInt(ean_code[i]);
        if (i%2 == 0) {
          sum += digit;
        }
        else {
          sum += 3*digit;
        }
      }
      ean_checksum = Math.ceil(sum/10)*10-sum;
      
      return ean_code + ean_checksum;
    }

    window.create_ean13 = create_ean13;
})();
