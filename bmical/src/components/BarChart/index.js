import { BarChart, Bar, CartesianGrid, XAxis, YAxis } from 'recharts';


const Chart = (props) => {

    console.log("graph component gdata ",props.gdata)

    return(
        <BarChart width={600} height={600} data={props.gdata}>
            <Bar dataKey="no" fill="green" />
            <CartesianGrid stroke="#ccc" />
            <XAxis dataKey="name" />
            <YAxis />
          </BarChart>
    )
}

export default Chart;