TRUE_IMAGE_EVAL_SCRIPT = """
        //VERSION=3
    
        function setup() {
            return {
                input: [{
                    bands: ["B02", "B03", "B04"]
                }],
                output: {
                    bands: 3
                }
            };
        }
    
        function evaluatePixel(sample) {
            return [sample.B04, sample.B03, sample.B02];
        }
    """

SAR1_EVAL_SCRIPT = """function setup() {
  return {
    input: ["VV", "dataMask"],
    output: [
      { id: "default", bands: 4 },
      { id: "eobrowserStats", bands: 1 },
      { id: "dataMask", bands: 1 },
    ],
  };
}

function evaluatePixel(samples) {
  const value = Math.max(0, Math.log(samples.VV) * 0.21714724095 + 1);
  return {
    default: [value, value, value, samples.dataMask],
    eobrowserStats: [Math.max(-30, (10 * Math.log10(samples.VV)))],
    dataMask: [samples.dataMask],
  };
}"""