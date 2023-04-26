const canvasSketch = require('canvas-sketch');
const {lerp}= require('canvas-sketch-util/math');
const random= require('canvas-sketch-util/random');
const palettes = require('nice-color-palettes')

const settings = {
  dimensions: [ 2048, 2048 ]
};

const sketch = () => {
  const colorCount = random.rangeFloor(2,6)
  const palette = random.shuffle(random.pick(palettes)).slice(0,colorCount)

  const createGrid = () => {
    const points = [];
    const count = 20;
  
    for(let x = 0; x < count; x++) {
      for(let y = 0; y < count; y++) {
        const u = count<1?0.5: x/(count-1);
        const v = count<1?0.5: y/(count-1);
        const radius = Math.abs(random.noise2D(u,v))*0.05;

        points.push({
          color:random.pick(palette),
          radius,
          rotation:random.noise2D(u,v),
          position:[u,v]
        });
      }
    }
    return points;
  }
  
  const points = createGrid().filter(()=> random.value() > 0.5);
  const margin = 200;

  return ({ context, width, height }) => {
    const c = context
    c.fillStyle = 'white'
    c.fillRect(0,0,width,height)

    points.forEach(({
      position,
      radius,
      color,
      rotation
    }) => {
      const [u,v] = position;
      const x = lerp(margin,width-margin,u)
      const y = lerp(margin,height-margin,v);

      // c.beginPath();
      // c.arc(x,y,radius*width,0,Math.PI*2,false);
      // c.fillStyle=color;
      // c.fill()

      c.save()
      c.beginPath();
      c.fillStyle=color;
      c.font= `${radius*width}px "Helvetica"`
      c.translate(x,y);
      c.rotate(rotation)
      c.fillText('send nudes',0,0)

      c.restore()
    });
  };
};

canvasSketch(sketch, settings);