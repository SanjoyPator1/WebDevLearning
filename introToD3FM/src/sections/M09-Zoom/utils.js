import {colors} from './color';

export const timelineColorFinder = (
  status,
  isAfterCurrentDate
) => {
  const blueSecondaryColor = colors.secondary.blue;
  const blueTertiaryColor = colors.neutral.blue;

  if (isAfterCurrentDate) {
    return ["#ff9f43", '#FFFFFF', "#ff9f43"];
  }

  let primaryColor, secondaryColor, tertiaryColor;

  switch (status) {
    case 'In Progress':
      primaryColor = colors.primary.orange;
      secondaryColor = colors.secondary.orange;
      break;
    case 'Pending':
      primaryColor = colors.primary.gray;
      secondaryColor = colors.secondary.gray;
      break;
    case 'Completed':
      primaryColor = colors.primary.green;
      secondaryColor = colors.secondary.green;
      break;
    default:
      primaryColor = bsPrimary;
      secondaryColor = blueSecondaryColor;
      tertiaryColor = blueTertiaryColor;
      break;
  }

  return [primaryColor, secondaryColor, tertiaryColor];
};

export function formatDataForTimeline(
  startDate,
  endDate,
  data
) {
  const formattedStartDate = typeof startDate === 'string' ? new Date(startDate) : startDate;

  const formattedEndDate = typeof endDate === 'string' ? new Date(endDate) : endDate;

  const formattedData= data.map((item) => {
    const date = typeof item.date === 'string' ? new Date(item.date) : (item.date );

    return {
      ...item,
      date: new Date(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()),
    };
  });

  return {
    startDate: formattedStartDate,
    endDate: formattedEndDate,
    formattedData: formattedData,
  };
}

export function formatDateForTimeline(date) {
  const formattedDate = typeof date === 'string' ? new Date(date) : date;

  return new Date(
    formattedDate.getUTCFullYear(),
    formattedDate.getUTCMonth(),
    formattedDate.getUTCDate()
  );
}
