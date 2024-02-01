
import { Grid } from '@mui/material';
import { IconAlt, IconChecklist, IconMessageDots, IconCalendarTime } from '@tabler/icons-react';
import * as d3 from 'd3';
import React, { useEffect, useRef, useState } from 'react';
import ReactDOMServer from 'react-dom/server';
import { dummyProjectTimelineData } from './constant';
import { formatDataForTimeline, formatDateForTimeline, timelineColorFinder } from './utils';
import {colors} from './color';

const svgHeight = 140;

const E3TimelineGraphAdvanced = () => {
  const timelineData = dummyProjectTimelineData;
  let xAxisGroup;
  let divGroup;
  let xAxisGridLines;
  let yAxisGridLines;
  const currentDate = formatDateForTimeline(new Date());
  const contentIconDimension = 30;
  const svgRef = useRef(null);
  const parentRef = useRef(null);
  const svgPaintedOnceRef = useRef(false);
  const [parentWidth, setParentWidth] = useState(0);

  // Function to draw the current date line
  function drawCurrentDateLine(
    svg,
    currentDate,
    xScale
  ){
    // Remove existing line
    svg.selectAll('.current-date-line').remove();

    // Draw new line
    svg
      .append('line')
      .attr('class', 'current-date-line')
      .attr('x1', () => {
        const curPos = xScale(currentDate);
        // console.log(currentDate, curPos);
        return curPos;
      })
      .attr('y1', 0)
      .attr('x2', xScale(currentDate))
      .attr('y2', svgHeight)
      .attr('stroke', colors.secondary.red)
      .attr('stroke-width', 1);
  }

  // set current parent rect size according to screen size
  useEffect(() => {
    const handleResize = () => {
      if (parentRef.current) {
        const parentWidth = parentRef.current.getClientRects()[0].width;
        setParentWidth(parentWidth);
      }
    };

    handleResize(); // Call handleResize on first render

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [parentRef.current]);

  useEffect(() => {
    const svg = d3.select(svgRef.current);

    const minDate = new Date(
      Math.min(...timelineData.content.map((item) => new Date(item.date).getTime()))
    );

    const maxDate = new Date(
      Math.max(...timelineData.content.map((item) => new Date(item.date).getTime()))
    );

    // Add extra months before and after the start and end dates
    const extraMonths = 1; // You can adjust this value as needed
    const startDateRaw = new Date(minDate);
    startDateRaw.setUTCMonth(startDateRaw.getUTCMonth() - extraMonths);
    const endDateRaw = new Date(maxDate);
    endDateRaw.setUTCMonth(endDateRaw.getUTCMonth() + extraMonths);

    const { startDate, endDate, formattedData } = formatDataForTimeline(
      startDateRaw,
      endDateRaw,
      timelineData.content
    );

    // console.log({ startDate, endDate, formattedData });

    svgPaintedOnceRef.current = true;

    // console.log('painting');

    // Clear the SVG
    svg.selectAll('*').remove();

    // Creating X scale based on time
    const xScale = d3
      .scaleTime()
      .domain([startDate, endDate])
      .range([0, parentWidth || 0]);
    const xAxis = d3.axisBottom(xScale);

    // Initial transformation for the timeline view
    const initialMonthTransform = d3.zoomIdentity
      .scale(parentWidth / (xScale(endDate) - xScale(startDate)))
      .translate(0, 0);

    // Zoom behavior definition
    const zoom = d3
      .zoom()
      .scaleExtent([1, 40])
      .translateExtent([
        [0, 0],
        [parentWidth || 0, svgHeight],
      ])
      .on('zoom', zoomed);

    // Setting up the SVG with zoom behavior and initial transformation
    svg
      .attr('width', '100%')
      .attr('height', svgHeight)
      .call(zoom)
      .call(zoom.transform, initialMonthTransform);

    // Adding a background rectangle to the SVG
    svg.append('rect').attr('width', '100%').attr('height', svgHeight).attr('fill', colors.neutral.blue);

    // Adding X axis to the SVG
    xAxisGroup = svg
      .append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${svgHeight / 2 + 40})`)
      .call(xAxis.tickFormat((date) => d3.timeFormat('%b - %Y')(date)));

    // Creating X axis grid lines
    const tickValues = xScale.ticks();

    // Calculate additional lines between existing ticks
    const additionalLines = [];
    for (let i = 0; i < tickValues.length - 1; i++) {
      const interval = (tickValues[i + 1].getTime() - tickValues[i].getTime()) / 5;
      for (let j = 1; j <= 4; j++) {
        const additionalTick = tickValues[i].getTime() + j * interval;
        additionalLines.push(new Date(additionalTick));
      }
    }

    const allTicks = tickValues.concat(additionalLines);

    xAxisGridLines = svg
      .append('g')
      .attr('class', 'x-axis-grid')
      .selectAll('line')
      .data(allTicks)
      .enter()
      .append('line')
      .attr('x1', (d) => xScale(d))
      .attr('y1', 0)
      .attr('x2', (d) => xScale(d))
      .attr('y2', svgHeight)
      .attr('stroke', (d) =>
        formattedData.find((item) => item.date === d) ? '#029FE3' : colors.secondary.blue
      )
      .attr('stroke-width', (d) => (formattedData.find((item) => item.date === d) ? 2 : 1));

    // Creating Y axis grid lines
    yAxisGridLines = svg
      .append('g')
      .attr('class', 'y-axis-grid')
      .selectAll('line')
      .data(d3.range(0, svgHeight, 10))
      .enter()
      .append('line')
      .attr('x1', 0)
      .attr('y1', (d) => d)
      .attr('x2', parentWidth)
      .attr('y2', (d) => d)
      .attr('stroke', (d) => (d === svgHeight / 2 ? '#029FE3' : colors.secondary.blue))
      .attr('stroke-width', (d) => (d === svgHeight / 2 ? 1 : 0.5))
      .attr('stroke-opacity', (d) => (d === svgHeight / 2 ? 0.7 : 1))
      .attr('stroke-dasharray', (d) => (d === svgHeight / 2 ? '10,10' : 'none'));

    // Adding a horizontal line that passes through the center
    // of the icons and circles and goes through the entire graph
    svg
      .append('line')
      .attr('x1', 0)
      .attr('y1', svgHeight / 2)
      .attr('x2', parentWidth)
      .attr('y2', svgHeight / 2)
      .attr('stroke', colors.primary.blue)
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '10,10');

    // Call the function to draw the current date line initially
    drawCurrentDateLine(svg, currentDate, xScale);

    const circleGroup = svg.append('g').attr('class', 'circle-group');

    circleGroup
      .selectAll('circle')
      .data(formattedData)
      .enter()
      .append('circle')
      .attr('cx', (d) => xScale(d.date))
      .attr('cy', svgHeight / 2)
      .attr('r', 5)
      .attr('fill', (d) => {
        const isAfterCurrentDate = d.date > new Date() ? true : false;
        let [primaryColor, secondaryColor] = timelineColorFinder(
          d.ActivityStatus,
          isAfterCurrentDate
        );

        if (d.type === 'start') {
          (primaryColor = colors.primary.blue), (secondaryColor = 'transparent');
        }

        return primaryColor;
      })
      .on('mouseover', function (event, d) {
        const tooltipPosition = {
          x: event.offsetX,
          y: event.offsetY - 20,
        };

        // console.log('circle tooltip ', tooltipPosition);

        const tooltipContent = (
          <div
            style={{
              background: '#333',
              color: '#fff',
              padding: '5px',
              borderRadius: '5px',
              fontSize: '12px',
            }}
          >
            {d3.timeFormat('%d %b')(d.date)} - {d.title}
          </div>
        );

        const tooltipString = ReactDOMServer.renderToString(tooltipContent);

        svg
          .append('foreignObject')
          .attr('class', 'tooltip')
          .attr('width', 150)
          .attr('height', 40)
          .attr('x', tooltipPosition.x)
          .attr('y', tooltipPosition.y)
          .html(() => tooltipString);
      })
      .on('mouseout', function () {
        svg.select('.tooltip').remove();
      });

    divGroup = svg.append('g').attr('class', 'div-group');

    divGroup
      .selectAll('.timeline-event')
      .data(formattedData)
      .enter()
      .append('foreignObject')
      .attr('class', 'timeline-event')
      .attr('width', contentIconDimension)
      .attr('height', 50)
      .attr('x', (d) => xScale(d.date) - contentIconDimension / 2)
      .attr('y', svgHeight / 2 - 40)
      .style('display', 'block')
      .html((d, i, nodes) => {
        const node = nodes[i];
        const content = formattedData[i];

        let IconComponent;
        const isAfterCurrentDate = content.date > new Date() ? true : false;
        let [primaryColor, secondaryColor] = timelineColorFinder(
          content.ActivityStatus,
          isAfterCurrentDate
        );

        if (content.type === 'start') {
          (primaryColor = colors.primary.blue), (secondaryColor = 'transparent');
        }

        // Use a switch statement to handle different icon types
        switch (content.type) {
          case 'start':
            IconComponent = () => (
              <div
                style={{
                  borderRadius: '100%',
                  aspectRatio: '1/1',
                  height: '100%',
                  width: '100%',
                  border: `5px solid #00CFE829`,
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                }}
              >
                <div
                  style={{
                    borderRadius: '100%',
                    aspectRatio: '1/1',
                    backgroundColor: primaryColor,
                    width: '100%',
                    height: '100%',
                  }}
                />
              </div>
            );
            break;
          case 'meeting':
            IconComponent = IconCalendarTime;
            break;
          case 'task':
            IconComponent = IconChecklist;
            break;
          default:
            IconComponent = IconAlt;
        }

        const commentsCount = content.notifications ? content.notifications.length : 0;

        const contentElement = (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'space-between',
              height: '100%',
              width: '100%',
            }}
          >
            {/* notification section */}
            <div
              style={{
                height: '45%',
                display: 'flex',
                justifyContent: 'flex-end',
              }}
            >
              {commentsCount && i > 0 ? (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '2px',
                  }}
                >
                  <IconMessageDots size={20} strokeWidth={1} style={{ color: '#555' }} />
                  <p style={{ fontSize: '12px' }}>{commentsCount}</p>
                </div>
              ) : (
                ''
              )}
            </div>
            {/* content icon section */}
            <div
              className={'content-icon'}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '55%',
                width: '70%',
                backgroundColor: secondaryColor,
                color: primaryColor,
                borderRadius: '6px',
                padding: '3px',
                border: d.type!=="start" ? `1px solid ${primaryColor}` : '',
              }}
            >
              <IconComponent
                strokeWidth={2}
                size={20}
                style={{
                  pointerEvents: 'none',
                }}
              />
            </div>
          </div>
        );

        const contentString = ReactDOMServer.renderToString(contentElement);

        node.innerHTML = contentString;

        return contentString;
      })
      .on('mouseover', function (event, d) {
        const transform = d3.zoomTransform(svgRef.current);

        // Calculate position relative to the document
        const tooltipPosition = {
          x: transform.applyX(event.clientX),
          y: transform.applyY(event.clientY),
        };

        // console.log('content tooltip ', tooltipPosition);

        const tooltipContent = (
          <div
            style={{
              background: '#333',
              color: '#fff',
              padding: '5px',
              borderRadius: '5px',
              fontSize: '12px',
            }}
          >
            {d.title}
          </div>
        );

        const tooltipString = ReactDOMServer.renderToString(tooltipContent);

        svg
          .append('foreignObject')
          .attr('class', 'tooltip')
          .attr('width', 150)
          .attr('height', 40)
          .attr('x', tooltipPosition.x)
          .attr('y', tooltipPosition.y)
          .html(() => tooltipString);
      })
      .on('mouseout', function () {
        svg.select('.tooltip').remove();
      });

    //working
    function zoomed(event) {
      const { transform } = event;
      const newXScale = transform.rescaleX(xScale);

      if (!xAxisGroup || !divGroup || !xAxisGridLines || !yAxisGridLines || !currentDate) return;

      // Clear existing grid lines during zoom
      xAxisGridLines.remove();

      // Calculate additional lines between existing ticks
      const tickValues = newXScale.ticks();
      const additionalLines = [];

      for (let i = 0; i < tickValues.length - 1; i++) {
        const additionalTick = (tickValues[i].getTime() + tickValues[i + 1].getTime()) / 2;
        additionalLines.push(new Date(additionalTick));
      }

      const allTicks = tickValues.concat(additionalLines);

      // Creating X axis grid lines during zoom
      xAxisGridLines = svg
        .append('g')
        .attr('class', 'x-axis-grid')
        .selectAll('line')
        .data(allTicks)
        .enter()
        .append('line')
        .attr('x1', (d) => newXScale(d))
        .attr('y1', 0)
        .attr('x2', (d) => newXScale(d))
        .attr('y2', svgHeight)
        .attr('stroke', (d) =>
          formattedData.find((item) => item.date === d) ? '#029FE3' : '#029FE329'
        )
        .attr('stroke-width', (d) => (formattedData.find((item) => item.date === d) ? 2 : 1));

      // Updating X axis and tick labels during zoom
      xAxisGroup.call(xAxis.scale(newXScale));

      // Adjusting tick labels based on zoom level
      if (transform.k > 8) {
        const tickValues = allTicks.map((tick) => new Date(tick));
        xAxisGroup.selectAll('.tick text').text((_, i) => {
          const formattedDate = d3.timeFormat('%d %b - %y')(tickValues[i]);
          // console.log(`Tick at position ${newXScale(tickValues[i])} with date ${formattedDate}`);
          return formattedDate;
        });
      } else {
        const tickValues = allTicks.map((tick) => new Date(tick));
        xAxisGroup.selectAll('.tick text').text((_, i) => {
          const formattedDate = d3.timeFormat('%b - %Y')(tickValues[i]);
          // console.log(`Tick at position ${newXScale(tickValues[i])} with date ${formattedDate}`);
          return formattedDate;
        });
      }

      // Call the function to update the current date line position
      drawCurrentDateLine(svg, currentDate, newXScale);

      const isZoomedIn = transform.k > 8;

      // Toggle visibility of circles and divGroup based on zoom level
      svg
        .selectAll('circle')
        .style('display', isZoomedIn ? 'none' : 'block');

      // Updating circle positions based on new X scale during zoom
      svg.selectAll('circle').attr('cx', (d) => {
        const xPosition = newXScale(d.date);
        // console.log(`Circle at position ${xPosition} for date ${d.date}`);
        return xPosition;
      });

      // Updating divGroup positions based on new X scale during zoom
      divGroup
        .selectAll('.timeline-event')
        .attr('x', (d) => newXScale(d.date) - contentIconDimension / 2);

      divGroup.style('display', isZoomedIn ? 'block' : 'none');
    }
  }, [parentWidth]);

  return (
    <Grid
      container
      sx={{
        backgroundColor: colors.neutral.blue,
        overflowX: 'scroll',
      }}
    >
      <div ref={parentRef} style={{ width: '100%' }}>
        <svg
          ref={svgRef}
          width={parentWidth}
          height={svgHeight}
          style={{
            boxShadow: 'inset 0px -8px 10px #00000012',
            border: "1px dashed"
          }}
        />
      </div>
    </Grid>
  );
};

export default E3TimelineGraphAdvanced;
